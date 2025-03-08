import requests
import urllib.request
import pprint


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()
    api_url = os.getenv("S2_API_URL", "http://api.semanticscholar.org/datasets/v1")


    # Get info about the latest release
    releases = requests.get(f"{api_url}/release").json()
    # Releases is a list of strings, each string is a release ID (Which corresponds to a date of release)
    latest_release = requests.get(f"{api_url}/release/latest").json()
    latest_release_id = latest_release['release_id']
    # Latest_release is a dictionary with keys 'release_id', 'datasets', 'README'.
    # 'datasets' is a list of dictionaries with keys 'name', 'description', 'README'.
    # print(latest_release['README'])
    print("Latest Release:", latest_release_id)

    # Earliest release
    earliest_release_id = min(releases)
    print("Earliest Release:", earliest_release_id)
    earliest_release = requests.get(f"{api_url}/release/{earliest_release_id}").json()

    # Print names of datasets in the release
    release_id = latest_release['release_id']
    print("Datasets in Latest Release:", ", ".join(d['name'] for d in latest_release['datasets']))

    papers_dataset = list(filter(lambda x: x['name'] == "papers", latest_release['datasets']))[0]
    print("Papers Dataset:")
    print("\n".join(map(lambda x: "    " + x, str.splitlines(papers_dataset['description']))))

    # Get info about the papers dataset
    papers = requests.get(f"{api_url}/release/{latest_release_id}/dataset/papers", 
                          headers={'X-API-KEY':os.getenv("S2_API_KEY")}).json()
    
    # Download the first part of the dataset
    urllib.request.urlretrieve(papers['files'][0], "papers-part0.jsonl.gz")