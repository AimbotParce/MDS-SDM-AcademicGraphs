from pathlib import Path
import requests
import urllib.request
from tqdm import tqdm

class SemanticScholarAPI:
    def __init__(self, api_url:str, api_key:str=None):
        self.api_url = api_url
        self.api_key = api_key

    def get(self, endpoint:str):
        return requests.get(f"{self.api_url}/{endpoint}", headers={'X-API-KEY':self.api_key}).json()
        

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
                print(f"WARNING: File {output_file} already exists. Skipping.")
                continue
            else:
                if progressbar:
                    bar = tqdm(unit="B", unit_scale=True, leave=False, desc=f"Downloading {output_file.name}", ascii=" ▏▎▍▌▋▊▉█")
                    def report(block_num, block_size, total_size):
                        bar.total = total_size
                        bar.update(block_num * block_size - bar.n)
                else:
                    print(f"Downloading {output_file}")
                    report = None
                try:
                    urllib.request.urlretrieve(file, output_file, reporthook=report)
                except KeyboardInterrupt:
                    print("Download interrupted. Cleaning up.")
                    output_file.unlink()
                    raise KeyboardInterrupt
                except Exception as e:
                    print(f"ERROR: {e}")
                    output_file.unlink()
                    break
                finally:
                    if progressbar:
                        bar.close()
                        print(f"Downloaded {output_file}")
        print("Download complete.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()
    api_url = os.getenv("S2_API_URL", "http://api.semanticscholar.org/datasets/v1")
    api_key = os.getenv("S2_API_KEY")
    api = SemanticScholarAPI(api_url, api_key)


    # Get all releases
    release_ids = api.get("release")
    # Releases is a list of strings, each string is a release ID (Which corresponds to a date of release)
    
    print("Earliest Release:", min(release_ids))
    latest_release_id = max(release_ids)
    print("Latest Release:", latest_release_id)


    # Get all information from latest release
    latest_release = api.get(f"release/{latest_release_id}")
    # Release information is a dictionary with keys 'release_id', 'datasets', 'README'.
    # 'datasets' is a list of dictionaries with keys 'name', 'description', 'README'.
    print("Datasets in Latest Release:", ", ".join(d['name'] for d in latest_release['datasets']))

    # We're interested in the papers dataset

    # Get info about the papers dataset
    papers_dataset = api.get(f"release/{latest_release_id}/dataset/papers")
    # Papers dataset is a dictionary with keys 'name', 'description', 'README' and 'files'

    print("Papers Dataset:")
    print("\n".join(map(lambda x: "    " + x, str.splitlines(papers_dataset['description']))))
    papers_files = papers_dataset['files']
    print("Papers Dataset Files:", len(papers_files))
    
    # Download the papers dataset files
    api.downloadDatasetFiles(latest_release_id, 'papers', 'data')
    print("Data downloaded. Remember to unzip the files using 'gzip -dk data/*.gz'")