import csv
import glob
import json
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import List

import requests
from loguru import logger
from tqdm import tqdm

from lib.io import BatchedWriter
from lib.models import *


def yieldFromFiles(files: List[Path]):
    """
    Loads CSV files sequentially and yields the rows one by one in a dictionary format.
    """
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic data for the academic graph.")
    parser.add_argument(
        "types", type=str, nargs="+", help="Data types to generate", choices=["reviews", "cities", "proceedings-cities"]
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory where the already prepared dataset is stored",
        required=True,
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=float("inf"),
        help="Batch size to write the generated data",
    )
    args = parser.parse_args()

    types: list[str] = args.types

    batch_size: int = args.batch_size
    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    if "reviews" in types:
        logger.info("Generating reviews")
        # Check if there exists already a "papers" csv file, as well as an "authors"
        # csv file, and a "wrote" csv file
        papers_files = sorted(output_dir.glob("nodes-papers-*.csv"))
        authors_files = sorted(output_dir.glob("nodes-authors-*.csv"))
        wrote_files = sorted(output_dir.glob("edges-wrote-*.csv"))

        if not papers_files:
            logger.error("No papers files found in the output directory")
            exit(1)
        if not authors_files:
            logger.error("No authors files found in the output directory")
            exit(1)
        if not wrote_files:
            logger.error("No wrote files found in the output directory")
            exit(1)

        random.seed(42)  # For reproducibility, we'll set a seed here

        with BatchedWriter(output_dir / "edges-reviewed-{batch}.csv", batch_size) as output_file:
            writer = csv.DictWriter(output_file, fieldnames=["authorID", "paperID"])
            writer.writeheader()

            author_pool: set[str] = set()
            # We'll create an author pool and we'll use it to generate the reviews
            for author in yieldFromFiles(authors_files):
                author_pool.add(author["authorID"])
            author_pool = list(sorted(author_pool))  # Need to sort here for reproducibility

            authorship_generator = yieldFromFiles(wrote_files)
            # We'll use a small trick here. Because we know that the authorship files, the authors and the papers
            # files were all generated in the same order, we can assume that the authorship files
            # are sorted in the same order as the papers were generated. Thus, we don't need to
            # perform a full-scale join here, we can iterate over both files in parallel.
            # We'll use the authorship to exclude the authors of the paper from the reviews

            total_papers = 0
            total_reviews = 0
            try:
                last_author = next(authorship_generator)
            except StopIteration:
                logger.error("No authorship files found in the output directory")
                exit(1)
            for paper in tqdm(yieldFromFiles(papers_files), desc="Preparing Reviews", unit="reviews", leave=False):
                total_papers += 1
                paper_id = paper["paperID"]

                # Get the authors of the paper
                this_paper_authors: set[str] = set()
                # We'll use this to exclude the authors of the paper from the reviews
                while last_author["paperID"] == paper_id:
                    this_paper_authors.add(last_author["authorID"])
                    try:
                        last_author = next(authorship_generator)
                    except StopIteration:
                        break
                # Generate the reviews
                # We'll generate between 3 and 5 reviews per paper
                num_reviews = random.randint(3, 5)
                reviewers: set[str] = set()
                while len(reviewers) < num_reviews:
                    reviewer = random.choice(author_pool)
                    if reviewer not in reviewers and reviewer not in this_paper_authors:
                        reviewers.add(reviewer)
                # Write the reviews
                for reviewer in reviewers:
                    total_reviews += 1
                    writer.writerow({"authorID": reviewer, "paperID": paper_id})

        logger.info(f"Generated {total_reviews} reviews for {total_papers} papers")
    if "cities" in types:
        logger.info("Generating cities")

        # Construct a pool of cities from the "cities API"
        url = "https://countriesnow.space/api/v0.1/countries"
        for _ in range(5):
            try:
                response = requests.get(url)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                logger.warning(f"Error fetching data from {url}: {e}. Retrying in 1s...")
                time.sleep(1)
        else:
            logger.error("Failed to fetch data from the API after 5 attempts.")
            exit(1)
        try:
            data = response.json()
        except:
            logger.error("Failed to parse JSON response from the API.")
            exit(1)
        if not data.get("data"):
            logger.error("No data found in the API response.")
            exit(1)
        with BatchedWriter(output_dir / "nodes-cities-{batch}.csv", batch_size) as output_file:
            writer = csv.DictWriter(output_file, fieldnames=["name"])
            writer.writeheader()

            cities = set()  # To avoid duplicates
            for country in data["data"]:
                country_name = country["country"]
                if not country_name == "Spain":
                    # We'll only include Spain for now, as it has too many cities
                    continue
                if "cities" in country:
                    for city in country["cities"]:
                        city_name = f"{country_name}/{city}"
                        cities.add(city_name)
                        writer.writerow({"name": city_name})
        logger.info(f"Generated {len(cities)} cities")

    if "proceedings-cities" in types:
        logger.info("Generating proceedings' cities")
        # Check if there exists already a "proceedings" csv file,
        # as well as a "cities" csv file

        proceedings_files = sorted(output_dir.glob("nodes-proceedings-*.csv"))
        cities_files = sorted(output_dir.glob("nodes-cities-*.csv"))

        if not proceedings_files:
            logger.error("No proceedings files found in the output directory")
            exit(1)
        if not cities_files:
            logger.error("No cities files found in the output directory")
            exit(1)

        # We'll use the cities files to generate the proceedings' cities
        cities: set[str] = set()
        for city in yieldFromFiles(cities_files):
            cities.add(city["name"])
        cities = list(sorted(cities))  # Need to sort here for reproducibility

        random.seed(42)  # For reproducibility, we'll set a seed here

        with BatchedWriter(output_dir / "edges-isheldin-{batch}.csv", batch_size) as output_file:
            writer = csv.DictWriter(output_file, fieldnames=["proceedingsID", "city"])
            writer.writeheader()

            total_proceedings = 0

            # We'll use the proceedings files to generate the proceedings' cities
            for proceeding in tqdm(
                yieldFromFiles(proceedings_files), desc="Preparing Proceedings' Cities", unit="proceedings", leave=False
            ):
                proceeding_id = proceeding["proceedingsID"]
                # Generate a random city for the proceeding
                city = random.choice(cities)
                writer.writerow({"proceedingsID": proceeding_id, "city": city})
                total_proceedings += 1

        logger.info(f"Generated {total_proceedings} proceedings' cities")
