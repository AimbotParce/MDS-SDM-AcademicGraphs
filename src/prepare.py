import csv
import json
import os
from io import TextIOBase
from pathlib import Path
from typing import List

from loguru import logger
from tqdm import tqdm

from lib.models import *


def yieldFromFiles(files: List[Path]):
    for file in files:
        with open(file, "r") as f:
            yield from map(json.loads, f)


class BatchedWriter(TextIOBase):
    def __init__(self, file: os.PathLike, batch_size: int):
        self.file = str(file)
        # Check whether file has the "{batch}" placeholder
        if "{batch}" not in self.file:
            raise ValueError("File must have the '{batch}' placeholder")
        self.batch_size = batch_size

        self.batch_number = 1
        self.current_batch_size = 0
        self._is_closed = False
        self.output_file = open(self.file.format(batch=self.batch_number), "w")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def write(self, line: str):
        if self._is_closed:
            raise ValueError("I/O operation on closed file")
        if self.current_batch_size >= self.batch_size:
            self.output_file.close()
            self.batch_number += 1
            self.current_batch_size = 0
            self.output_file = open(self.file.format(batch=self.batch_number), "w")
        self.output_file.write(line)
        self.current_batch_size += 1

    def writelines(self, lines: List[str]):
        for line in lines:
            self.write(line)

    def flush(self):
        self.output_file.flush()

    def close(self):
        if self._is_closed:
            return
        self._is_closed = True
        self.output_file.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare the Semantic Scholar dataset")
    parser.add_argument(
        "input_files",
        type=Path,
        nargs="+",
        help="Input JSONL files to prepare",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory to write the prepared dataset batches to",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        choices=["papers", "citations"],
        help="Type of file being loaded",
        required=True,
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size to write the prepared dataset",
    )
    args = parser.parse_args()

    input_files: list[Path] = args.input_files
    batch_size: int = args.batch_size
    file_type: str = args.type
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if file_type == "citations":
        with BatchedWriter(output_dir / "edges-citations-{batch}.csv", batch_size) as output_file:
            writer = csv.DictWriter(
                output_file, fieldnames=["citedPaperID", "citingPaperID", "isInfluential", "contextsWithIntent"]
            )
            writer.writeheader()
            for citation in tqdm(yieldFromFiles(input_files), desc="Preparing Citations", unit="citations"):
                writer.writerow(
                    {
                        "citedPaperID": citation["citedPaper"]["paperId"],
                        "citingPaperID": citation["citingPaper"]["paperId"],
                        "isInfluential": citation.get("isInfluential", False),
                        "contextsWithIntent": json.dumps(citation["contextsWithIntent"]),
                    }
                )
    elif file_type == "papers":
        papers = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-papers-{batch}.csv", batch_size),
            fieldnames=[
                "paperID",
                "url",
                "title",
                "abstract",
                "year",
                "isOpenAccess",
                "openAccessPDFUrl",
                "publicationTypes",
                "embedding",
                "tldr",
            ],
        )
        papers.writeheader()
        fieldsofstudy = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-fieldsofstudy-{batch}.csv", batch_size),
            fieldnames=["name"],
        )
        fieldsofstudy.writeheader()
        proceedings = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-proceedings-{batch}.csv", batch_size),
            fieldnames=["proceedingsID", "year"],
        )
        proceedings.writeheader()
        journalvolumes = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-journalvolumes-{batch}.csv", batch_size),
            fieldnames=["journalVolumeID", "year", "volume"],
        )
        journalvolumes.writeheader()
        journals = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-journals-{batch}.csv", batch_size),
            fieldnames=["journalID", "name", "url", "alternateNames"],
        )
        journals.writeheader()
        workshops = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-workshops-{batch}.csv", batch_size),
            fieldnames=["workshopID", "name", "url", "alternateNames"],
        )
        workshops.writeheader()
        conferences = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-conferences-{batch}.csv", batch_size),
            fieldnames=["conferenceID", "name", "url", "alternateNames"],
        )
        conferences.writeheader()
        cities = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-cities-{batch}.csv", batch_size),
            fieldnames=["name"],
        )
        cities.writeheader()
        authors = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-authors-{batch}.csv", batch_size),
            fieldnames=["authorID", "url", "name", "homepage", "hIndex"],
        )
        authors.writeheader()
        organizations = csv.DictWriter(
            BatchedWriter(output_dir / "nodes-organizations-{batch}.csv", batch_size),
            fieldnames=["name"],
        )
        organizations.writeheader()
        hasfieldofstudy = csv.DictWriter(
            BatchedWriter(output_dir / "edges-hasfieldofstudy-{batch}.csv", batch_size),
            fieldnames=["paperID", "fieldOfStudy"],
        )
        hasfieldofstudy.writeheader()
        wrote = csv.DictWriter(
            BatchedWriter(output_dir / "edges-wrote-{batch}.csv", batch_size),
            fieldnames=["paperID", "authorID"],
        )
        wrote.writeheader()
        mainauthor = csv.DictWriter(
            BatchedWriter(output_dir / "edges-mainauthor-{batch}.csv", batch_size),
            fieldnames=["paperID", "authorID"],
        )
        mainauthor.writeheader()
        isaffiliatedwith = csv.DictWriter(
            BatchedWriter(output_dir / "edges-isaffiliatedwith-{batch}.csv", batch_size),
            fieldnames=["authorID", "organization"],
        )
        isaffiliatedwith.writeheader()
        reviewed = csv.DictWriter(
            BatchedWriter(output_dir / "edges-reviewed-{batch}.csv", batch_size),
            fieldnames=["paperID", "authorID", "accepted", "minorRevisions", "majorRevisions", "reviewContent"],
        )
        reviewed.writeheader()
        ispublishedinjournal = csv.DictWriter(
            BatchedWriter(output_dir / "edges-ispublishedinjournal-{batch}.csv", batch_size),
            fieldnames=["paperID", "journalVolumeID", "pages"],
        )
        ispublishedinjournal.writeheader()
        ispublishedinproceedings = csv.DictWriter(
            BatchedWriter(output_dir / "edges-ispublishedinproceedings-{batch}.csv", batch_size),
            fieldnames=["paperID", "proceedingsID", "pages"],
        )
        ispublishedinproceedings.writeheader()
        iseditionofjournal = csv.DictWriter(
            BatchedWriter(output_dir / "edges-iseditionofjournal-{batch}.csv", batch_size),
            fieldnames=["journalVolumeID", "journalID"],
        )
        iseditionofjournal.writeheader()
        iseditionofconference = csv.DictWriter(
            BatchedWriter(output_dir / "edges-iseditionofconference-{batch}.csv", batch_size),
            fieldnames=["proceedingsID", "conferenceID"],
        )
        iseditionofconference.writeheader()
        iseditionofworkshop = csv.DictWriter(
            BatchedWriter(output_dir / "edges-iseditionofworkshop-{batch}.csv", batch_size),
            fieldnames=["proceedingsID", "workshopID"],
        )
        iseditionofworkshop.writeheader()
        isheldin = csv.DictWriter(
            BatchedWriter(output_dir / "edges-isheldin-{batch}.csv", batch_size),
            fieldnames=["proceedingsID", "city"],
        )
        isheldin.writeheader()

        unique_fields_of_study = set()
        unique_proceedings_ids = set()
        unique_journal_volume_ids = set()
        unique_journal_ids = set()
        unique_workshop_ids = set()
        unique_conference_ids = set()
        unique_city_names = set()
        unique_author_ids = set()
        unique_organization_names = set()
        for paper in tqdm(yieldFromFiles(input_files), desc="Preparing Papers", unit="papers"):
            papers.writerow(
                {
                    "paperID": paper["paperId"],
                    "url": paper["url"],
                    "title": paper["title"],
                    "abstract": paper["abstract"],
                    "year": paper["year"],
                    "isOpenAccess": paper["isOpenAccess"],
                    "openAccessPDFUrl": paper.get("openAccessPdfUrl"),
                    "publicationTypes": paper["publicationTypes"],
                    "embedding": json.dumps(paper.get("embedding")),
                    "tldr": paper.get("tldr"),
                }
            )
            for fos in paper["fieldsOfStudy"]:
                if not fos in unique_fields_of_study:
                    fieldsofstudy.writerow({"name": fos})
                    unique_fields_of_study.add(fos)
                hasfieldofstudy.writerow({"paperID": paper["paperId"], "fieldOfStudy": fos})
            for author in paper["authors"]:
                if author["authorId"] is None:
                    logger.warning(f"Author ID is None for author: {author}")
                    continue  # Skip this author
                if not author["authorId"] in unique_author_ids:
                    authors.writerow(
                        {
                            "authorID": author["authorId"],
                            "url": author["url"],
                            "name": author["name"],
                            "homepage": author.get("homepage"),
                            "hIndex": author.get("hIndex"),
                        }
                    )
                    unique_author_ids.add(author["authorId"])
                wrote.writerow({"paperID": paper["paperId"], "authorID": author["authorId"]})
                for affiliation in author["affiliations"]:
                    if not affiliation in unique_organization_names:
                        organizations.writerow({"name": affiliation})
                        unique_organization_names.add(affiliation)
                    isaffiliatedwith.writerow({"authorID": author["authorId"], "organization": affiliation})
            main_author = paper["authors"][0]  # We'll assume the first author is the main author
            mainauthor.writerow({"paperID": paper["paperId"], "authorID": main_author["authorId"]})

            # Publications
            venue = paper["publicationVenue"]
            if venue["type"] == "journal":
                if not venue["id"] in unique_journal_ids:
                    journals.writerow(
                        {
                            "journalID": venue["id"],
                            "name": venue["name"],
                            "url": venue.get("url"),
                            "alternateNames": json.dumps(venue["alternate_names"]),
                        }
                    )
                    unique_journal_ids.add(venue["id"])
                journal_volume_id = (venue["id"], paper["journal"]["volume"])
                if not journal_volume_id in unique_journal_volume_ids:
                    journalvolumes.writerow(
                        {
                            "journalVolumeID": json.dumps(list(journal_volume_id)),
                            "year": paper["year"],
                            "volume": paper["journal"]["volume"],
                        }
                    )
                    unique_journal_volume_ids.add(journal_volume_id)
                    iseditionofjournal.writerow(
                        {"journalVolumeID": json.dumps(list(journal_volume_id)), "journalID": venue["id"]}
                    )
                ispublishedinjournal.writerow(
                    {
                        "paperID": paper["paperId"],
                        "journalVolumeID": json.dumps(list(journal_volume_id)),
                        "pages": paper["journal"].get("pages"),
                    }
                )
            if venue["type"] == "conference":
                if not venue["id"] in unique_conference_ids:
                    conferences.writerow(
                        {
                            "conferenceID": venue["id"],
                            "name": venue["name"],
                            "url": venue.get("url"),
                            "alternateNames": json.dumps(venue["alternate_names"]),
                        }
                    )
                    unique_conference_ids.add(venue["id"])
                proceedings_id = (venue["id"], paper["year"])
                if not proceedings_id in unique_proceedings_ids:
                    proceedings.writerow({"year": paper["year"], "proceedingsID": json.dumps(list(proceedings_id))})
                    unique_proceedings_ids.add(proceedings_id)
                    iseditionofconference.writerow(
                        {"proceedingsID": json.dumps(list(proceedings_id)), "conferenceID": venue["id"]}
                    )
                    isheldin.writerow({"proceedingsID": json.dumps(list(proceedings_id)), "city": None})

                ispublishedinproceedings.writerow(
                    {
                        "paperID": paper["paperId"],
                        "proceedingsID": json.dumps(list(proceedings_id)),
                        "pages": paper.get("journal", {}).get("pages"),
                    }
                )
            if venue["type"] == "workshop":
                if not venue["id"] in unique_workshop_ids:
                    workshops.writerow(
                        {
                            "workshopID": venue["id"],
                            "name": venue["name"],
                            "url": venue.get("url"),
                            "alternateNames": json.dumps(venue["alternate_names"]),
                        }
                    )
                    unique_workshop_ids.add(venue["id"])
                proceedings_id = (venue["id"], paper["year"])
                if not proceedings_id in unique_proceedings_ids:
                    proceedings.writerow({"year": paper["year"], "proceedingsID": json.dumps(list(proceedings_id))})
                    unique_proceedings_ids.add(proceedings_id)
                    iseditionofworkshop.writerow(
                        {"proceedingsID": json.dumps(list(proceedings_id)), "workshopID": venue["id"]}
                    )
                    isheldin.writerow(
                        {"proceedingsID": json.dumps(list(proceedings_id)), "city": paper["journal"]["city"]}
                    )

                ispublishedinproceedings.writerow(
                    {
                        "paperID": paper["paperId"],
                        "proceedingsID": json.dumps(list(proceedings_id)),
                        "pages": paper.get("journal", {}).get("pages"),
                    }
                )

        logger.success("Dataset files prepared successfully")
        logger.warning("The following objects could not be extracted and will have to be generated manually:")
        logger.warning("- City of a conference/workshop")
        logger.warning("- Review details")
    else:
        raise ValueError(f"Unknown file type: {file_type}")
