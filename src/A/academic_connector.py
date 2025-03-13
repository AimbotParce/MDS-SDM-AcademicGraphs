import os
import json
import argparse
import time
from typing import TypedDict, Union, List, Dict
import requests

from loguru import logger
from pathlib import Path

# ===-----------------------------------------------------------------------===#
# Academic Graph API Connector                                                 #
#                                                                              #
# Author: Walter J.T.V                                                         #
# ===-----------------------------------------------------------------------===#


class S2AcademicAPIConnector:
    def __init__(self):
        self.paper_url = "https://api.semanticscholar.org/graph/v1/paper"
        self.author_url = "https://api.semanticscholar.org/graph/v1/author"
        self.api_key = os.getenv("S2_API_KEY")

    def fetch(
        self,
        url: str,
        api_params: dict,
        max_retries: int = 3,
        backoff: int = 2,
        strict_raise: bool = False,
    ) -> dict:

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(url, params=api_params)
                if strict_raise:
                    response.raise_for_status()
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    f"[Fetch] Attempt {attempt}/{max_retries} failed (Status {response.status_code})"
                )
                time.sleep(backoff**attempt)
            except requests.RequestException as e:
                logger.error(f"[Fetch] API request error: {e}")
        raise Exception(
            f"[Fetch] API request failed after {max_retries} retries: {url}"
        )

    # This function returns a list of papers ids stored in json dicts
    def bulk_retrieve_papers(self, params: dict) -> list[dict]:
        try:
            url = f"{self.paper_url}/search/bulk"
            data = self.fetch(url=url, api_params=params)
            return data
        except Exception as e:
            logger.error("Failed to do a bulk retrieval of papers")
            exit()

    def chunk_list(self, lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i : i + chunk_size]

    # This function returns a list of paper_details (dict/json) that can be identified by paperId
    def bulk_retrieve_details(self, data: list, params: dict) -> list[dict]:
        try:
            paper_ids = [paper["paperId"] for paper in data["data"]]

            if not paper_ids:
                logger.warning("[Bulk Retrieve] No paper IDs provided")
                return []

            url = f"{self.paper_url}/batch"
            chunk_size = 500
            paper_chunks = list(self.chunk_list(paper_ids, chunk_size))
            total_chunks = len(paper_chunks)

            logger.warning(
                f"[Bulk Retrieve] Sending {total_chunks} request(s) to the API (max {chunk_size} papers per request)."
            )

            all_results = []

            for index, chunk in enumerate(paper_chunks, start=1):
                try:
                    response = requests.post(url, params=params, json={"ids": chunk})
                    response.raise_for_status()

                    if response.status_code == 200:
                        logger.success(
                            f"[Chunk {index}/{total_chunks}] Successfully retrieved {len(chunk)} paper details."
                        )
                        all_results.extend(response.json())
                    else:
                        logger.error(
                            f"[Chunk {index}/{total_chunks}] Failed to fetch paper details: {response.status_code} - {response.text}"
                        )

                except requests.RequestException as req_err:
                    logger.error(
                        f"[Chunk {index}/{total_chunks}] Request failed: {req_err}"
                    )

            return all_results

        except Exception as e:
            logger.error(f"Exception in bulk_retrieve_details: {e}")
            return None

    def retrieve_citations(self, paper_id: str, params: dict) -> List[dict]:
        try:
            url = f"{self.paper_url}/{paper_id}/citations"
            data = self.fetch(url, api_params=params, backoff=0)
            return data
            logger.warning(f"No citations found for paper {paper_id}")
            return []
        except Exception as e:
            logger.error(f"Error fetching citations for {paper_id}: {e}")
            return []

    def retrieve_references(self, paper_id: str, params: dict) -> list:
        try:
            url = f"{self.paper_url}/{paper_id}/references"
            data = self.fetch(url, api_params=params, backoff=0)
            return data
            logger.warning(f"No references found for paper {paper_id}")
            return []
        except Exception as e:
            logger.error(f"Error fetching references for {paper_id}: {e}")
            return []


    def bulk_fetch_citations_and_references(
        self, data: list, cit_params: dict, ref_params: dict
    ) -> Union[dict, dict]:
        all_citations = []
        all_references = []
        for paper in data.get("data", []):
            paper_id = paper["paperId"]

            # Fetch citations
            citations = self.retrieve_citations(paper_id, cit_params)
            citations["paperId"] = paper_id
            all_citations.append(citations)

            # Fetch references
            references = self.retrieve_references(paper_id, ref_params)
            references["paperId"] = paper_id
            all_references.append(references)

        logger.success("Successfully retrieved citations and references for all papers.")
        return all_citations, all_references

    def bulk_retrieve_authors(self):
        pass







def save_json(data, filename):
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    file_path = DATA_DIR / filename  # Save inside 'data' folder
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    logger.success(f"Saved {file_path}")
# This main showcases how to extract the main relevant information
# - Papers details
# - Authors details
# - References
# - Citations
# - Venues
# - Embeddings
def main(args):
    connector = S2AcademicAPIConnector()

    if args.dry_run:
        logger.info("Running in DRY RUN mode. No data will be saved.")

    # Step 1: Retrieve Papers (4 in this case)
    compiler_params = {
        "query": "neural network",
        "sort": "citationCount:desc",
        "minCitationCount": 80000,
        "limit": 10000
    }
    bulk_papers = connector.bulk_retrieve_papers(compiler_params)
    logger.success(f"Retrieved {bulk_papers.get('total', 0)} papers.")

    # Step 2: Retrieve Paper Details
    details_params = {
        "fields": "isOpenAccess,journal,publicationDate,publicationVenue,fieldsOfStudy,title,abstract,url,year,embedding,tldr,citationCount,referenceCount,authors.authorId,authors.url,authors.name,authors.affiliations,authors.homepage,authors.hIndex",
    }
    bulk_details = connector.bulk_retrieve_details(bulk_papers, details_params)
    logger.success(f"Retrieved details for {len(bulk_details)} papers.")

    # Step 3: Retrieve Citations & References
    citations_params = {"fields": "contexts,title,authors,intents,isInfluential", "offset": 0}
    references_params = {"fields": "contexts,title,authors,intents,isInfluential", "offset": 0}
    citations, references = connector.bulk_fetch_citations_and_references(
        bulk_papers, citations_params, references_params
    )
    logger.success("Retrieved citations and references.")

    # Step 4: Save data (if not dry run)
    if not args.dry_run:
        save_json(bulk_papers, "bulk_papers.json")
        save_json(bulk_details, "bulk_details.json")
        save_json(citations, "citations.json")
        save_json(references, "references.json")
    else:
        logger.warning("Dry run complete. No data was saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Academic Paper Data Retrieval")
    parser.add_argument("--dry-run", action="store_true", help="Run without saving any data")
    args = parser.parse_args()
    main(args)