from pathlib import Path
import os
import json 
import time
from typing import TypedDict, Union
import requests

from loguru import logger

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
        
    def bulk_retrieve_papers(self, params: dict):
        try:
            url = f"{self.paper_url}/search/bulk" 
            data = self.fetch(url=url, api_params=params)
            return data
        except Exception as e:
            logger.error("Failed to do a bulk retrieval of papers")
            exit()
    

    def bulk_retrieve_details(self, data: list, params: dict):
        try:
            paper_ids = [paper["paperId"] for paper in data["data"]]
            
            if not paper_ids:
                logger.warning("[Bulk Retrieve] No paper IDs provided")
                return []

            url = f"{self.paper_url}/batch"
            response = requests.post(url, params=params, json={"ids": paper_ids})

            if response.status_code == 200:
                logger.success(f"Successfully retrieved {len(paper_ids)} paper details")
                return response.json()
            else:
                logger.error(f"Failed to fetch paper details: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Exception in bulk_retrieve_details: {e}")

    
    def retrieve_citations(self, paper_id: str, params: dict):
        try:
            url = f"{self.paper_url}/{paper_id}/citations"
            data = self.fetch(url, api_params=params, backoff=1)
            
            if data and "data" in data:
                return data["data"]
            logger.warning(f"No citations found for paper {paper_id}")
            return []
        except Exception as e:  
            logger.error(f"Error fetching citations for {paper_id}: {e}")
            return []
        
    def retrieve_references(self, paper_id: str, params: dict):
        try:
            url = f"{self.paper_url}/{paper_id}/references"
            data = self.fetch(url, api_params=params)
            
            if data and "data" in data:
                return "data"
            logger.warning(f"No references found for paper {paper_id}")
            return []
        except Exception as e:
            logger.error(f"Error fetching references for {paper_id}: {e}")
            return [] 

    def bulk_retrieve_citations_and_references(self, papers):
        pass 
    
    def bulk_retrieve_authors(self):
        pass


if __name__ == "__main__":
    
    connector = S2AcademicAPIConnector()
    
    compiler_params = {
        "query": "compiler machine learning",
        "sort": "citationCount:desc",
        "minCitationCount": 100,
    }
    
    dl_params = {
        "query": "deep learning",
        "sort": "citationCount:desc",
        "minCitationCount": 20
    }
    
    ml_params = {
        "query": "machine learning",
        "sort": "citationCount:desc",
        "minCitationCount": 20
    }
    
    params = compiler_params
        
    # Do a retrieval of a specific theme of topics
    bulk_papers = connector.bulk_retrieve_papers(params)
    logger.success(f"Extracted {bulk_papers["total"]} papers about {params["query"]}, and is a dictionary of keys: {bulk_papers.keys()}")
    #print(json.dumps(bulk_papers, indent=2))

    
    # Retrieve the details of those papers
    details_params = {
        "fields": "title,authors,abstract,year,citationCount,referenceCount,isOpenAccess",
    }
    bulk_details = connector.bulk_retrieve_details(bulk_papers)
    
    # Retrieve the details of those authors
    authors_params = {
        "fields": "citingPaper.paperId,citingPaper.title,citingPaper.authors",
        "offset": 0,
        "limit": 100
    }
    
    # Retrieve citations and references of those papers (2 endpoints)
    
    
    
    