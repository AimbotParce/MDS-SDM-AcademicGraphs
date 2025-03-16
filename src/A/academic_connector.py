import argparse
import json
import os
from itertools import batched
from pathlib import Path
from typing import Generator, Iterable, Iterator, List, Literal, Optional, Tuple, Union, overload

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

    @overload
    def bulk_retrieve_details(
        self, paper_ids: Iterable[str], fields: Iterable[str], batch_size: None
    ) -> List[dict]: ...

    @overload
    def bulk_retrieve_details(self, paper_ids: Iterable[str], fields: Iterable[str]) -> List[dict]: ...

    @overload
    def bulk_retrieve_details(
        self, paper_ids: Iterable[str], fields: Iterable[str], batch_size: int
    ) -> Generator[dict, None, None]: ...

    # This function returns a list of paper_details (dict/json) that can be identified by paperId
    def bulk_retrieve_details(self, paper_ids: Iterable[str], fields: Iterable[str], batch_size: Optional[int] = None):
        """
        Retrieve the details for a list of papers.

        Args:
            paper_ids (list[str]): The list of paper IDs to retrieve details for.
            fields (list[str]): The fields to return in the response.
            batch_size (int): The number of papers to retrieve per request.

        Returns:
            details (Generator[dict, None, None] | list[dict]): If the batch size is None, a list of paper details.
            Otherwise, a generator of paper details.
        """

        def _download_chunk(chunk: list[str]) -> list[dict]:
            return self.post("paper/batch", params={"fields": ",".join(fields)}, json={"ids": chunk})

        if batch_size is not None:
            if not batch_size > 0:
                raise ValueError("batch size must be greater than 0 or None")
            paper_chunks = batched(paper_ids, batch_size)
            total_chunks = len(paper_ids) // batch_size + ((len(paper_ids) % batch_size) > 0)
            logger.warning(
                f"[Bulk Retrieve] Sending {total_chunks} request(s) to the API (max {batch_size} papers per request)."
            )
            for chunk in paper_chunks:
                yield from _download_chunk(chunk)
        else:
            return _download_chunk(paper_ids)

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

    @overload
    def bulk_retrieve_citations(
        self, paper_ids: Iterable[str], fields: Iterable[str], stream: Literal[False]
    ) -> List[dict]: ...

    @overload
    def bulk_retrieve_citations(self, paper_ids: Iterable[str], fields: Iterable[str]) -> List[dict]: ...

    @overload
    def bulk_retrieve_citations(
        self, paper_ids: Iterable[str], fields: Iterable[str], stream: Literal[True]
    ) -> Generator[dict, None, None]: ...

    def bulk_retrieve_citations(self, paper_ids: Iterable[str], fields: Iterable[str], stream: bool = False):
        """
        Retrieve the citations for a list of papers.

        Args:
            paper_ids (list[str]): The list of paper IDs to retrieve citations for.
            fields (list[str]): The fields to return in the response.

        Returns:
            citations (Generator[dict, None, None] | List[dict]):
            If the batch size is None, a list of citations. Otherwise, a generator of citations.
        """

        def _download_citations(paper_id: str) -> List[dict]:
            _, _, citations = self.retrieve_citations(paper_id, fields)
            for citation in citations:
                citation["citedPaper"] = {"paperId": paper_id}
            return citations

        if not stream:
            all_citations = []
            for paper_id in paper_ids:
                citations = _download_citations(paper_id)
                all_citations.extend(citations)
            return all_citations
        else:
            for paper_id in paper_ids:
                yield from _download_citations(paper_id)

    @overload
    def bulk_retrieve_references(
        self, paper_ids: Iterable[str], fields: Iterable[str], stream: Literal[False]
    ) -> List[dict]: ...

    @overload
    def bulk_retrieve_references(self, paper_ids: Iterable[str], fields: Iterable[str]) -> List[dict]: ...

    @overload
    def bulk_retrieve_references(
        self, paper_ids: Iterable[str], fields: Iterable[str], stream: Literal[True]
    ) -> Generator[dict, None, None]: ...

    def bulk_retrieve_references(self, paper_ids: list[str], fields: list[str], stream: bool = False):
        """
        Retrieve the references for a list of papers.

        Args:
            paper_ids (list[str]): The list of paper IDs to retrieve references for.
            fields (list[str]): The fields to return in the response.

        Returns:
            references (Generator[dict, None, None] | List[dict]):
            If the batch size is None, a list of references. Otherwise, a generator of references.
        """

        def _download_references(paper_id: str) -> List[dict]:
            _, _, references = self.retrieve_references(paper_id, fields)
            for reference in references:
                reference["citingPaper"] = {"paperId": paper_id}
            return references

        if not stream:
            all_references = []
            for paper_id in paper_ids:
                references = _download_references(paper_id)
                all_references.extend(references)
            return all_references
        else:
            for paper_id in paper_ids:
                yield from _download_references(paper_id)


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
    total_papers, _, papers = connector.bulk_retrieve_papers("neural network", minCitationCount=80000)
    logger.success(f"Retrieved {total_papers} papers.")
    paper_ids: list[str] = list(paper["paperId"] for paper in papers)
    del papers  # Free up memory

    logger.info("Retrieving paper details...")
    missing_fields = (
        "paperId",
        "embedding",
        "tldr",
        "url",
        "title",
        "abstract",
        "year",
        "isOpenAccess",
        "openAccessPdf",
        "publicationTypes",
        # Author fields
        "authors.authorId",
        "authors.url",
        "authors.name",
        "authors.affiliations",
        "authors.homepage",
        "authors.hIndex",
        # Field of study fields
        "fieldsOfStudy",
        # Publication venue or journal
        "journal",
        "publicationVenue",
        # If the paper is published in a Journal, "journal" has the information about the page number and things
        # about the journal. Also, publicationVenue might have some extra information about it.
        # If it is published in the Proceedings of a conference, "publicationVenue" has the information about the
        # conference and "journal" might have some extra information about where in the proceedings the paper is.
    )
    paper_details = connector.bulk_retrieve_details(paper_ids, missing_fields, batch_size=500)
    total_details = 0
    for i, papers in enumerate(batched(paper_details, 1000), start=1):
        logger.info(f"[Batch {i}] Retrieved {len(papers)} paper details.")
        total_details += len(papers)
        if not args.dry_run:
            saveJSONL(papers, f"papers-{i}.jsonl")

    logger.success(f"Retrieved {total_details} paper details.")

    # Get all the citations
    logger.info("Retrieving citations...")
    citation_fields = "citingPaper.paperId", "isInfluential", "contextsWithIntent"
    citations = connector.bulk_retrieve_citations(paper_ids, citation_fields, stream=True)
    total_citations = 0
    for i, citations in enumerate(batched(citations, 1000), start=1):
        logger.info(f"[Batch {i}] Retrieved {len(citations)} citations.")
        total_citations += len(citations)
        if not args.dry_run:
            saveJSONL(citations, f"citations-{i}.jsonl")

    logger.success(f"Retrieved {total_citations} citations.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Academic Paper Data Retrieval")
    parser.add_argument("--dry-run", action="store_true", help="Run without saving any data")
    args = parser.parse_args()
    main(args)
