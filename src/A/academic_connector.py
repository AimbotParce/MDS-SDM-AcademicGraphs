import argparse
import json
import os
from itertools import batched
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union

from loguru import logger
from semantic_scholar_api import SemanticScholarAPI

# ===-----------------------------------------------------------------------===#
# Academic Graph API Connector                                                 #
#                                                                              #
# Authors: Walter J.T.V, Marc Parcerisa                                        #
# ===-----------------------------------------------------------------------===#


class S2AcademicAPI(SemanticScholarAPI):
    def __init__(
        self,
        api_url: str = "https://api.semanticscholar.org/graph/v1",
        api_key: str = None,
        default_max_retries: int = 1,
        default_backoff: float = 2,
    ):
        super().__init__(api_url, api_key, default_max_retries, default_backoff)

    # This function returns a list of papers ids stored in json dicts
    def bulk_retrieve_papers(
        self,
        query: str,
        token: str = None,
        fields: list[str] = None,
        sort: str = None,
        publicationTypes: list[str] = None,
        openAccessPdf: bool = False,
        minCitationCount: int = None,
        publicationDateOrYear: str = None,
        year: str = None,
        venue: list[str] = None,
        fieldsOfStudy: list[str] = None,
    ) -> Tuple[int, str, list[dict]]:
        """
        Retrieve a list of papers based on a query.

        Args:
            query (str): The query string to search for.
            token (str): The cursor token to use for pagination.
            fields (list[str]): The fields to return in the response.
            sort (str): The field to sort by.
            publicationTypes (list[str]): The publication types to filter by.
            openAccessPdf (bool): Whether to filter by open access PDF.
            minCitationCount (int): The minimum citation count to filter by.
            publicationDateOrYear (str): The publication date or year to filter by. (e.g. 2021-01-01, 2021 or 2015:2018)
            year (str): The year to filter by. (e.g. 2021 or 2015:2018)
            venue (list[str]): The venue to filter by.
            fieldsOfStudy (list[str]): The fields of study to filter by.

        Returns:
            Tuple[int, str, list[dict]]: The total number of papers, the next token, and the list of papers.
        """

        params = {"query": query}
        if token:
            params["token"] = token
        if fields:
            params["fields"] = ",".join(fields)
        if sort:
            params["sort"] = sort
        if publicationTypes:
            params["publicationTypes"] = ",".join(publicationTypes)
        if openAccessPdf:
            params["openAccessPdf"] = openAccessPdf
        if minCitationCount:
            params["minCitationCount"] = minCitationCount
        if publicationDateOrYear:
            params["publicationDateOrYear"] = publicationDateOrYear
        if year:
            params["year"] = year
        if venue:
            params["venue"] = ",".join(venue)
        if fieldsOfStudy:
            params["fieldsOfStudy"] = ",".join(fieldsOfStudy)

        try:
            data = self.get("paper/search/bulk", params=params)
            return data["total"], data["token"], data["data"]
        except Exception as e:
            logger.error("Failed to do a bulk retrieval of papers")
            raise e

    # This function returns a list of paper_details (dict/json) that can be identified by paperId
    def bulk_retrieve_details(self, paper_ids: list[str], fields: list[str], batch_size: int = None) -> list[dict]:
        """
        Retrieve the details for a list of papers.

        Args:
            paper_ids (list[str]): The list of paper IDs to retrieve details for.
            fields (list[str]): The fields to return in the response.
            batch_size (int): The number of papers to retrieve per request.

        Returns:
            list[dict]: The list of paper details.
        """
        try:
            if batch_size is not None:
                if not batch_size > 0:
                    raise ValueError("batch size must be greater than 0 or None")
                paper_chunks = list(batched(paper_ids, batch_size))
                logger.warning(
                    f"[Bulk Retrieve] Sending {len(paper_chunks)} request(s) to the API (max {batch_size} papers per request)."
                )
            else:
                paper_chunks = [paper_ids]

            all_results = []
            for index, chunk in enumerate(paper_chunks, start=1):
                try:
                    response = self.post("paper/batch", params={"fields": ",".join(fields)}, json={"ids": chunk})
                except Exception as req_err:
                    logger.error(f"[Chunk {index}/{len(paper_chunks)}] Request failed: {req_err}")
                else:
                    all_results.extend(response)
            return all_results

        except Exception as e:
            logger.error(f"Exception in bulk_retrieve_details: {e}")
            return None

    def retrieve_citations(
        self, paper_id: str, fields: list[str], limit: int = None, offset: int = None
    ) -> Tuple[Optional[int], Optional[int], List[dict]]:
        """
        Retrieve the citations for a paper.

        Args:
            paper_id (str): The paper ID to retrieve citations for.
            fields (list[str]): The fields to return in the response.
            limit (int): The number of citations to return.
            offset (int): The offset to start from.

        Returns:
            Tuple[int, int, List[dict]]: The starting position of this batch,
            the starting position of the next batch, and the list of citations.
        """
        params = {"fields": ",".join(fields)}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        try:
            data = self.get(f"paper/{paper_id}/citations", params=params)
            return data["offset"], data.get("next"), data["data"]
        except Exception as e:
            logger.error(f"Error fetching citations for {paper_id}: {e}")
            return None, None, []

    def retrieve_references(
        self, paper_id: str, fields: list[str], limit: int = None, offset: int = None
    ) -> Tuple[Optional[int], Optional[int], List[dict]]:
        """
        Retrieve the references for a paper.

        Args:
            paper_id (str): The paper ID to retrieve references for.
            fields (list[str]): The fields to return in the response.
            limit (int): The number of references to return.
            offset (int): The offset to start from.

        Returns:
            Tuple[int, int, List[dict]]: The starting position of this batch,
            the starting position of the next batch, and the list of references.
        """
        params = {"fields": ",".join(fields)}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        try:
            data = self.get(f"paper/{paper_id}/references", params=params)
            return data["offset"], data.get("next"), data["data"]
        except Exception as e:
            logger.error(f"Error fetching references for {paper_id}: {e}")
            return None, None, []

    def bulk_retrieve_citations(self, paper_ids: list[str], fields: list[str]) -> Tuple[int, List[dict]]:
        """
        Retrieve the citations for a list of papers.

        Args:
            paper_ids (list[str]): The list of paper IDs to retrieve citations for.
            fields (list[str]): The fields to return in the response.

        Returns:
            Tuple[int, List[dict]]: The total number of citations and the list of all citations.
        """
        all_citations = []
        citation_count = 0
        for paper_id in paper_ids:
            _, _, citations = self.retrieve_citations(paper_id, fields)
            for citation in citations:
                citation["citedPaper"] = {"paperId": paper_id}
            all_citations.extend(citations)
            citation_count += len(citations)
        return citation_count, all_citations

    def bulk_retrieve_references(self, paper_ids: list[str], fields: list[str]) -> Tuple[int, List[dict]]:
        """
        Retrieve the references for a list of papers.

        Args:
            paper_ids (list[str]): The list of paper IDs to retrieve references for.
            fields (list[str]): The fields to return in the response.

        Returns:
            Tuple[int, List[dict]]: The total number of references and the list of all references.
        """
        all_references = []
        reference_count = 0
        for paper_id in paper_ids:
            _, _, references = self.retrieve_references(paper_id, fields)
            for reference in references:
                reference["citingPaper"] = {"paperId": paper_id}
            all_references.extend(references)
            reference_count += len(references)
        return reference_count, all_references

    def bulk_retrieve_authors(self):
        pass


def saveJSONL(data: list[dict], filename):
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    file_path = DATA_DIR / filename  # Save inside 'data' folder
    with open(file_path, "w", encoding="utf-8") as f:
        for line in data:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")  # Write each dict as a JSON line

    logger.success(f"Saved {file_path}")


# This main showcases how to extract the main relevant information
# - Papers details
# - Authors details
# - References
# - Citations
# - Venues
# - Embeddings
def main(args):
    connector = S2AcademicAPI(api_key=os.getenv("S2_API_KEY"), default_max_retries=3)

    if args.dry_run:
        logger.info("Running in DRY RUN mode. No data will be saved.")

    # Step 1: Retrieve Papers (4 in this case)
    total, token, bulk_papers = connector.bulk_retrieve_papers(
        "neural network", sort="citationCount:desc", minCitationCount=80000
    )
    logger.success(f"Retrieved {total} papers.")
    paper_ids: list[str] = list(paper["paperId"] for paper in bulk_papers)

    if not args.dry_run:
        saveJSONL(bulk_papers, "papers.jsonl")
    del bulk_papers  # Free up memory

    # Step 2: Retrieve Paper Details
    fields = (
        "isOpenAccess",
        "journal",
        "publicationDate",
        "publicationVenue",
        "fieldsOfStudy",
        "title",
        "abstract",
        "url",
        "year",
        "embedding",
        "tldr",
        "citationCount",
        "referenceCount",
        "authors.authorId",
        "authors.url",
        "authors.name",
        "authors.affiliations",
        "authors.homepage",
        "authors.hIndex",
    )

    bulk_details = connector.bulk_retrieve_details(paper_ids, fields)
    logger.success(f"Retrieved details for {len(bulk_details)} papers.")

    if not args.dry_run:
        saveJSONL(bulk_details, "details.jsonl")
    del bulk_details  # Free up memory

    # Step 3: Retrieve Citations & References
    citation_fields = "contexts", "title", "authors", "intents", "isInfluential"
    total, citations = connector.bulk_retrieve_citations(paper_ids, citation_fields)
    logger.success(f"Retrieved {total} citations.")

    if not args.dry_run:
        saveJSONL(citations, "citations.jsonl")
    del citations  # Free up memory

    reference_fields = "contexts", "title", "authors", "intents", "isInfluential"
    total, references = connector.bulk_retrieve_references(paper_ids, reference_fields)
    logger.success(f"Retrieved {total} references.")

    if not args.dry_run:
        saveJSONL(references, "references.jsonl")
    del references  # Free up memory

    if args.dry_run:
        logger.warning("Dry run complete. No data was saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Academic Paper Data Retrieval")
    parser.add_argument("--dry-run", action="store_true", help="Run without saving any data")
    args = parser.parse_args()
    main(args)
