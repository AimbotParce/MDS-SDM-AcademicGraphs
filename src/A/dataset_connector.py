import urllib.request
from pathlib import Path
from typing import TypedDict, Union

import requests
from loguru import logger
from tqdm import tqdm


class SemanticScholarAPI:
    def __init__(self, api_url: str, api_key: str = None):
        self.api_url = api_url
        self.api_key = api_key

        self._releases: dict[str, Release] = {}

    def get(self, endpoint: str):

        try:
            raw_res = requests.get(f"{self.api_url}/{endpoint}", headers={"X-API-KEY": self.api_key})
            raw_res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                json_res = raw_res.json()
                logger.error(f"Error from {self.api_url}/{endpoint}: {json_res['message']}")
            except Exception:
                logger.error(f"Error from {self.api_url}/{endpoint}: {e}")
            raise e
        try:
            json_res = raw_res.json()
        except Exception as e:
            logger.error(f"Error decoding response from {self.api_url}/{endpoint}: {e}")
            raise e

        if "message" in json_res:
            logger.error(f"Error from {self.api_url}/{endpoint}: {json_res['message']}")
            raise Exception(json_res["message"])
        return json_res

    def getReleaseIDs(self) -> list[str]:
        return self.get("release")  # No cache. They shouldn't change often, but if they do, we'll get the latest info

    def getRelease(self, release_id: str) -> "Release":
        if release_id in self._releases:
            return self._releases[release_id]
        else:
            self._releases[release_id] = Release(self.get(f"release/{release_id}"), self)
            return self._releases[release_id]


class PrunedDatasetData(TypedDict):
    name: str
    description: str
    README: str


class DatasetData(PrunedDatasetData):
    files: list[str]


class ReleaseData(TypedDict):
    release_id: str
    datasets: list[PrunedDatasetData]
    README: str


class Release(object):
    def __init__(self, data: ReleaseData, api: SemanticScholarAPI):
        self.data = data
        self.api = api

        self._datasets = {}

    @property
    def release_id(self):
        return self.data["release_id"]

    @property
    def README(self):
        return self.data["README"]

    def getDatasetNames(self):
        return [dataset["name"] for dataset in self.data["datasets"]]

    def getDataset(self, dataset_name: str) -> "Dataset":
        if dataset_name in self._datasets:
            return self._datasets[dataset_name]
        else:
            for dataset in self.data["datasets"]:
                if dataset["name"] == dataset_name:
                    self._datasets[dataset_name] = Dataset(
                        self.api.get(f"release/{self.release_id}/dataset/{dataset_name}"), self
                    )
                    return self._datasets[dataset_name]

            raise KeyError(f"Dataset {dataset_name} not found in release {self.release_id}")


class Dataset(object):
    def __init__(self, data: DatasetData, release: Release):
        self.data = data
        self.release = release

    @property
    def name(self):
        return self.data["name"]

    @property
    def description(self):
        return self.data["description"]

    @property
    def README(self):
        return self.data["README"]

    @property
    def files(self):
        return self.data["files"]

    def printInfo(self):
        logger.info(f"{self.name.capitalize()} Dataset ({len(self.files)} files):")
        for line in str.splitlines(self.description):
            logger.info("    " + line)

    def downloadFiles(self, output_dir: Path, max_files: int = None, progressbar: bool = True):
        output_dir = Path(output_dir)
        zeros = len(str(len(self.files)))
        for i, file in enumerate(self.files, 1):
            if max_files and i > max_files:
                break
            output_file = output_dir / f"rel-{self.release.release_id}-{self.name}-{i:0{zeros}d}.jsonl.gz"
            if output_file.exists():
                logger.warning(f"File {output_file} already exists. Skipping.")
                continue
            else:
                if progressbar:
                    bar = tqdm(
                        unit="B",
                        unit_scale=True,
                        leave=False,
                        desc=f"Downloading {output_file.name}",
                        ascii=" ▏▎▍▌▋▊▉█",
                    )

                    def report(block_num, block_size, total_size):
                        bar.total = total_size
                        bar.update(block_num * block_size - bar.n)

                else:
                    logger.info(f"Downloading {output_file}")
                    report = None
                try:
                    urllib.request.urlretrieve(file, output_file, reporthook=report)
                except KeyboardInterrupt:
                    logger.warning("Download interrupted. Cleaning up.")
                    output_file.unlink()
                    raise KeyboardInterrupt
                except Exception as e:
                    logger.error(str(e))
                    output_file.unlink()
                    break
                else:
                    logger.info(f"Downloaded {output_file}")
                finally:
                    if progressbar:
                        bar.close()


if __name__ == "__main__":
    import argparse
    import os
    import time

    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description="Download the Semantic Scholar dataset")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Don't download anything")
    args = parser.parse_args()

    load_dotenv()
    api_url = os.getenv("S2_API_URL", "http://api.semanticscholar.org/datasets/v1")
    api_key = os.getenv("S2_API_KEY")
    api = SemanticScholarAPI(api_url, api_key)

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
