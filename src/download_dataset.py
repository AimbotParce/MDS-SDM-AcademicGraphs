import argparse
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from lib.semantic_scholar import S2DatasetAPI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download the Semantic Scholar dataset")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Don't download anything")
    args = parser.parse_args()

    load_dotenv()
    api_url = os.getenv("S2_API_URL", "http://api.semanticscholar.org/datasets/v1")
    api_key = os.getenv("S2_API_KEY")
    api = S2DatasetAPI(api_url, api_key)

    # Get all releases
    release_ids = api.getReleaseIDs()
    # Releases is a list of strings, each string is a release ID (Which corresponds to a date of release)

    logger.info(f"Earliest Release: {min(release_ids)}")
    latest_release_id = max(release_ids)
    logger.info(f"Latest Release: {latest_release_id}")

    # Get all information from latest release
    latest_release = api.getRelease(latest_release_id)
    # Release information is a dictionary with keys 'release_id', 'datasets', 'README'.
    # 'datasets' is a list of dictionaries with keys 'name', 'description', 'README'.
    logger.info(f"Datasets in Latest Release: {', '.join(latest_release.getDatasetNames())}")

    # Print the information of each dataset
    # Each dataset info is a dictionary with keys 'name', 'description', 'README' and 'files'
    for dataset_name in latest_release.getDatasetNames():
        while True:
            try:
                dataset = latest_release.getDataset(dataset_name)
            except Exception as e:
                logger.warning("Retrying...")
                time.sleep(1)
                continue
            else:
                dataset.printInfo()
                break

    if not args.dry_run:
        logger.info("Downloading data...")

        # Download all files from the latest release
        latest_release.getDataset("publication-venues").downloadFiles(Path("data"))
        latest_release.getDataset("papers").downloadFiles(Path("data"), max_files=5)

        logger.info("Data downloaded. Remember to unzip the files using 'gzip -dk data/*.gz'")
