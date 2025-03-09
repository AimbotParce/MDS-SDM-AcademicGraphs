from pathlib import Path
import requests
import urllib.request
from tqdm import tqdm
from loguru import logger

class SemanticScholarAPI:
    def __init__(self, api_url:str, api_key:str=None):
        self.api_url = api_url
        self.api_key = api_key

    def get(self, endpoint:str):

        try:
            raw_res = requests.get(f"{self.api_url}/{endpoint}", headers={'X-API-KEY':self.api_key})
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
        
        if 'message' in json_res:
            logger.error(f"Error from {self.api_url}/{endpoint}: {json_res['message']}")
            raise Exception(json_res['message'])
        return json_res
            

        

    def downloadDatasetFiles(self, release_id:str, dataset_name:str, output_dir:Path, max_files:int=None, progressbar:bool=True):
        output_dir = Path(output_dir)
        dataset = self.get(f"release/{release_id}/dataset/{dataset_name}")
        files = dataset['files']
        zeros = len(str(len(files)))
        for i, file in enumerate(files, 1):
            if max_files and i > max_files:
                break
            output_file = output_dir / f"rel-{release_id}-{dataset_name}-{i:0{zeros}d}.jsonl.gz"
            if output_file.exists():
                logger.warning(f"File {output_file} already exists. Skipping.")
                continue
            else:
                if progressbar:
                    bar = tqdm(unit="B", unit_scale=True, leave=False, desc=f"Downloading {output_file.name}", ascii=" ▏▎▍▌▋▊▉█")
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
                finally:
                    if progressbar:
                        bar.close()
                        logger.info(f"Downloaded {output_file}")
        logger.info("Download complete.")

    def printDatasetInfo(self, release_id: str, dataset_name:str):
        info = self.get(f"release/{release_id}/dataset/{dataset_name}")
        logger.info(f"{dataset_name.capitalize()} Dataset:")
        for line in str.splitlines(info['description']):
            logger.info("    " + line)
        papers_files = info['files']
        logger.info(f"{dataset_name.capitalize()} Dataset Files: {len(papers_files)}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    import argparse
    import os
    import sys

    parser = argparse.ArgumentParser(description="Download the Semantic Scholar dataset")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Don't download anything")
    args = parser.parse_args()

    load_dotenv()
    api_url = os.getenv("S2_API_URL", "http://api.semanticscholar.org/datasets/v1")
    api_key = os.getenv("S2_API_KEY")
    api = SemanticScholarAPI(api_url, api_key)


    # Get all releases
    release_ids = api.get("release")
    # Releases is a list of strings, each string is a release ID (Which corresponds to a date of release)
    
    logger.info(f"Earliest Release: {min(release_ids)}")
    latest_release_id = max(release_ids)
    logger.info(f"Latest Release: {latest_release_id}")


    # Get all information from latest release
    latest_release = api.get(f"release/{latest_release_id}")
    # Release information is a dictionary with keys 'release_id', 'datasets', 'README'.
    # 'datasets' is a list of dictionaries with keys 'name', 'description', 'README'.
    logger.info(f"Datasets in Latest Release: {', '.join(d['name'] for d in latest_release['datasets'])}")


    # Get info and data from the different datasets.
    # Each dataset info is a dictionary with keys 'name', 'description', 'README' and 'files'

    ########################################################
    #                    Papers Dataset                    #
    ########################################################

    api.printDatasetInfo(latest_release_id, 'papers')
    if not args.dry_run:    
        api.downloadDatasetFiles(latest_release_id, 'papers', 'data')

    ########################################################
    #                   Authors Dataset                    #
    ########################################################

    api.printDatasetInfo(latest_release_id, 'authors')
    if not args.dry_run:    
        api.downloadDatasetFiles(latest_release_id, 'authors', 'data')


    ########################################################
    #                  Citations Dataset                   #
    ########################################################

    api.printDatasetInfo(latest_release_id, 'citations')
    if not args.dry_run:    
        api.downloadDatasetFiles(latest_release_id, 'citations', 'data')



    if not args.dry_run:
        logger.info("Data downloaded. Remember to unzip the files using 'gzip -dk data/*.gz'")