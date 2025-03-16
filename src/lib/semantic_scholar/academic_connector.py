import argparse
import json
import os
from itertools import batched
from pathlib import Path
from typing import Generator, Iterable, List, Literal, Optional, Tuple, Union, overload

from loguru import logger

from .api_connector import SemanticScholarAPI

# ===-----------------------------------------------------------------------===#
# Academic Graph API Connector                                                 #
#                                                                              #
# Authors: Walter J.T.V, Marc Parcerisa                                        #
# ===-----------------------------------------------------------------------===#


class S2AcademicAPI(SemanticScholarAPI):
    MAX_BATCH_SIZE = 1000
    MAX_DATA_RETRIEVAL = 10_000

    def __init__(
        self,
        api_url: str = "https://api.semanticscholar.org/graph/v1",
        api_key: str = None,
        default_max_retries: int = 1,
        default_backoff: float = 2,
    ):
        super().__init__(api_url, api_key, default_max_retries, default_backoff)

    @overload
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
        limit: int = None,
    ) -> list[dict]: ...

    @overload
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
        limit: int = None,
        stream: Literal[False] = False,
    ) -> list[dict]: ...

    @overload
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
        limit: int = None,
        stream: Literal[True] = False,
    ) -> Generator[dict, None, None]: ...

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
        limit: int = None,
        stream: bool = False,
    ):
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
            papers (list[dict] | Generator[dict, None, None]): If stream is False, a list of papers.
            Otherwise, a generator of papers.
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

        if not stream:
            data = self.get("paper/search/bulk", params=params)
            result = data["data"]
            while data.get("token"):
                if limit is not None and len(result) >= limit:
                    break
                data = self.get("paper/search/bulk", params={**params, "token": data["token"]})
                result.extend(data["data"])
            return result[:limit] if limit else result
        else:
            data = self.get("paper/search/bulk", params=params)
            total_yielded = 0
            if limit is not None and len(data["data"]) > limit:
                yield from data["data"][0:limit]
                total_yielded += limit
            else:
                yield from data["data"]
                total_yielded += len(data["data"])
            while data.get("token"):
                if limit is not None and total_yielded >= limit:
                    break
                data = self.get("paper/search/bulk", params={**params, "token": data["token"]})
                if limit is not None and len(data["data"]) + total_yielded > limit:
                    yield from data["data"][0 : limit - total_yielded]
                    total_yielded += limit - total_yielded
                else:
                    yield from data["data"]
                    total_yielded += len(data["data"])

    @overload
    def bulk_retrieve_details(self, paper_ids: Iterable[str], fields: Iterable[str]) -> List[dict]: ...
    @overload
    def bulk_retrieve_details(
        self, paper_ids: Iterable[str], fields: Iterable[str], stream: Literal[False]
    ) -> List[dict]: ...
    @overload
    def bulk_retrieve_details(
        self, paper_ids: Iterable[str], fields: Iterable[str], stream: Literal[True]
    ) -> Generator[dict, None, None]: ...

    # This function returns a list of paper_details (dict/json) that can be identified by paperId
    def bulk_retrieve_details(self, paper_ids: Iterable[str], fields: Iterable[str], stream: bool = False):
        """
        Retrieve the details for a list of papers.

        Args:
            paper_ids (list[str]): The list of paper IDs to retrieve details for.
            fields (list[str]): The fields to return in the response.
            stream (bool): Whether to stream the results.

        Returns:
            details (Generator[dict, None, None] | List[dict]): If stream is False, a list of paper details.
            Otherwise, a generator of paper details.
        """

        def _download_chunk(chunk: list[str]) -> List[dict]:
            return self.post("paper/batch", params={"fields": ",".join(fields)}, json={"ids": chunk})

        if stream or len(paper_ids) > self.MAX_BATCH_SIZE:
            paper_chunks = batched(paper_ids, self.MAX_BATCH_SIZE)
            for chunk in paper_chunks:
                yield from _download_chunk(chunk)
        else:
            return _download_chunk(paper_ids)

    @overload
    def retrieve_citations(self, paper_id: str, fields: list[str]) -> List[dict]: ...
    @overload
    def retrieve_citations(self, paper_id: str, fields: list[str], stream: Literal[False]) -> List[dict]: ...
    @overload
    def retrieve_citations(
        self, paper_id: str, fields: list[str], stream: Literal[True]
    ) -> Generator[dict, None, None]: ...

    def retrieve_citations(
        self, paper_id: str, fields: list[str], stream: bool = False
    ) -> Union[List[dict], Generator[dict, None, None]]:
        """
        Retrieve the citations for a paper.

        Args:
            paper_id (str): The paper ID to retrieve citations for.
            fields (list[str]): The fields to return in the response.
            stream (bool): Whether to stream the results.

        Returns:
            citations (list[dict] | Generator[dict, None, None]): If stream is False, a list of citations.
            Otherwise, a generator of citations.
        """
        params = {"fields": ",".join(fields)}

        data = self.get(f"paper/{paper_id}/citations", params=params)
        if stream:
            yield from data["data"]
        else:
            all_data = data["data"]

        while data.get("next"):
            if data.get("next") >= self.MAX_DATA_RETRIEVAL - 1:
                # This seems to be a hard limit of the Semantic Scholar API
                logger.warning(
                    f"Citation count exceeds {self.MAX_DATA_RETRIEVAL}. "
                    f"Only the first {self.MAX_DATA_RETRIEVAL} citations will be retrieved."
                )
                break
            data = self.get(
                f"paper/{paper_id}/citations",
                params={
                    **params,
                    "offset": data["next"],
                    "limit": min(self.MAX_BATCH_SIZE, self.MAX_DATA_RETRIEVAL - data["next"] - 1),
                },
            )
            if stream:
                yield from data["data"]
            else:
                all_data.extend(data["data"])
        if not stream:
            return all_data

    @overload
    def retrieve_references(self, paper_id: str, fields: list[str]) -> List[dict]: ...
    @overload
    def retrieve_references(self, paper_id: str, fields: list[str], stream: Literal[False]) -> List[dict]: ...
    @overload
    def retrieve_references(
        self, paper_id: str, fields: list[str], stream: Literal[True]
    ) -> Generator[dict, None, None]: ...

    def retrieve_references(
        self, paper_id: str, fields: list[str], stream: bool = False
    ) -> Union[List[dict], Generator[dict, None, None]]:
        """
        Retrieve the references for a paper.

        Args:
            paper_id (str): The paper ID to retrieve references for.
            fields (list[str]): The fields to return in the response.
            stream (bool): Whether to stream the results.

        Returns:
            references (list[dict] | Generator[dict, None, None]): If stream is False, a list of references.
            Otherwise, a generator of references.
        """
        params = {"fields": ",".join(fields)}

        data = self.get(f"paper/{paper_id}/references", params=params)
        if stream:
            yield from data["data"]
        else:
            all_data = data["data"]

        while data.get("next"):
            if data.get("next") >= self.MAX_DATA_RETRIEVAL - 1:
                # This seems to be a hard limit of the Semantic Scholar API
                logger.warning(
                    f"Reference count exceeds {self.MAX_DATA_RETRIEVAL}. "
                    f"Only the first {self.MAX_DATA_RETRIEVAL} references will be retrieved."
                )
                break
            data = self.get(
                f"paper/{paper_id}/references",
                params={
                    **params,
                    "offset": data["next"],
                    "limit": min(self.MAX_BATCH_SIZE, self.MAX_DATA_RETRIEVAL - data["next"] - 1),
                },
            )
            if stream:
                yield from data["data"]
            else:
                all_data.extend(data["data"])
        if not stream:
            return all_data

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

        def _download_citations(paper_id: str):
            citations = self.retrieve_citations(paper_id, fields, stream=stream)
            all_citations = []
            for citation in citations:
                citation["citedPaper"] = {"paperId": paper_id}
                if stream:
                    yield citation
                else:
                    all_citations.append(citation)
            if not stream:
                return all_citations

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

        def _download_references(paper_id: str):
            references = self.retrieve_references(paper_id, fields, stream=stream)
            all_references = []
            for reference in references:
                reference["citingPaper"] = {"paperId": paper_id}
                if stream:
                    yield reference
                else:
                    all_references.append(reference)
            if not stream:
                return all_references

        if not stream:
            all_references = []
            for paper_id in paper_ids:
                references = _download_references(paper_id)
                all_references.extend(references)
            return all_references
        else:
            for paper_id in paper_ids:
                yield from _download_references(paper_id)
