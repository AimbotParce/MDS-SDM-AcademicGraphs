import yake
from neo4j import GraphDatabase
import pandas as pd
from dotenv import load_dotenv
import os
import json
from loguru import logger
from typing import List, Dict, Optional
import re
import argparse


load_dotenv()
neo4j_username = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
# Connect to Neo4j
driver = GraphDatabase.driver(
    "bolt://localhost:7687", auth=(neo4j_username, neo4j_password)
)

######
###### Keyword NLP extraction (Python)
######


# Function to extract keywords with model flexibility (batch processing)
def extract_keywords_from_combination_batch(
    papers: pd.DataFrame,
    max_ngram: int = 2,
    num_keywords: int = 5,
    dedupthreshold: float = 0.9,
) -> dict:
    kw_extractor = yake.KeywordExtractor(
        lan="en", n=max_ngram, top=num_keywords, dedupLim=dedupthreshold
    )
    paper_keywords = {}

    for _, row in papers.iterrows():
        paper_id = row["paperID"]
        title = row["title"]
        tldr = row.get("tldr", "")  # Could be missing
        abstract = row.get("abstract", "")  # Could be missing

        # Combine title with tldr if available, otherwise fallback to abstract
        if isinstance(tldr, str) and tldr.strip():
            combined_text = f"{title} {tldr}"
        elif isinstance(abstract, str) and abstract.strip():
            combined_text = f"{title} {abstract}"
        else:
            combined_text = f"{title}"

        # JUST IN CASE SANITY CHECK :) --> return empty dicc
        if not combined_text.strip():
            paper_keywords

        if combined_text.strip():
            keywords = kw_extractor.extract_keywords(combined_text)
            paper_keywords[paper_id] = [kw for kw, _ in keywords]

    return paper_keywords


# Function to insert keywords into Neo4j and associate them with papers
def insert_keywords(tx, paper_id: str, keywords: list[str]):
    for kw in keywords:
        tx.run(
            """
            MERGE (k:KeyWord {name: $keyword})
            WITH k  // Use WITH to pass `k` to the next part of the query
            MATCH (p:Publication {paperID: $paper_id})
            MERGE (p)-[:HasKeyWord]->(k)
        """,
            keyword=kw,
            paper_id=paper_id,
        )


# Preprocess and update Neo4j with keywords for each paper
def preprocess_keywords_and_update_graph(
    paper_df: pd.DataFrame,
    max_ngram: int = 2,
    num_keywords: int = 5,
    dedupthreshold: float = 0.9,
):
    with driver.session() as session:
        # Extract keywords in batch (for all papers)
        paper_keywords = extract_keywords_from_combination_batch(
            paper_df, max_ngram, num_keywords, dedupthreshold
        )

        # Insert extracted keywords into Neo4j
        for paper_id, keywords in paper_keywords.items():
            if keywords:  # Ensure there are keywords to insert
                session.execute_write(insert_keywords, paper_id, keywords)


# Function to fetch papers from Neo4j
def fetch_papers_from_neo4j():
    query = """
    MATCH (N:Publication)
    RETURN N.paperID as paperID, N.title as title, N.abstract as abstract, N.tldr as tldr
    """

    with driver.session() as session:
        result = session.run(query)
        papers = []
        for record in result:
            tldr = record["tldr"]
            if isinstance(tldr, str):
                try:
                    tldr_dict = json.loads(tldr)  # Attempt to parse the JSON string
                    tldr = tldr_dict.get(
                        "text", None
                    )  # Get the 'text' field from the parsed JSON
                except json.JSONDecodeError:
                    tldr = None  # If tldr is not a valid JSON, set to empty string

            papers.append(
                {
                    "paperID": record["paperID"],
                    "title": record["title"],
                    "tldr": tldr,
                    "abstract": record["abstract"],
                }
            )
        return papers


######
###### Reviewer recommendation (Cypher)
######


def run_query(tx, query):
    tx.run(query)

def to_camel_case(name: str) -> str:
    parts = re.split(r'[\s_-]+', name)
    return ''.join(word.capitalize() for word in parts) 

#Encapsulate LABEL logic in these functions to avoid hardcoding and low locality of behaviour
def get_community_venue_label(community_name: str):
    return to_camel_case(community_name) + "Venue"

def get_community_toppaper_label(community_name: str):
    return f"Top{community_name}Paper"

def get_community_reviewer_label(community_name: str):
    return f"{community_name}Reviewer"

def get_community_guru_label(community_name: str):
    return f"{community_name}Guru"

# This statement generates:
# 1. A community
# 2. Keywords related to that community
# 3. Edges from community<->keyword
def step1_recsys_define_community(tx,
    community: str = "Database",
    keywords: List[str] = [
      "data management", "indexing", "data modeling",
      "big data", "data processing", "data storage", "data querying"
    ])->None:
    
    keywords_cypher = "[" + ", ".join(f'"{kw}"' for kw in keywords) + "]"

    query = f"""
    MERGE (c:Community {{name: "{community}"}})
    WITH c, {keywords_cypher} AS keywords
    UNWIND keywords as kw
    MERGE (k: KeyWord {{name: kw}})
    MERGE (c)-[:HasKeyWord]->(k)
    """
    run_query(tx, query)


# This statement searches the venues related to that community
# through a simple percentage (papers that have any keyword related vs rest in venue)
# and labels that venue as a community-venue
def step2_recsys_label_venues(tx,
    community: str = "Database",
    percentage: float = 0.001):
    
    query = f"""
    MATCH (c:Community {{name: "{community}"}})-[:HasKeyWord]->(k:KeyWord)       // Get community and its keywords
    MATCH (v)<-[:IsPublishedIn]-(p:Publication)-[:HasKeyWord]->(k)                // Get venues and keywords of a paper
    WHERE v:Proceedings OR v:JournalVolume OR v.OtherPublicationVenue
    WITH v, COUNT(DISTINCT p) as related_papers
    MATCH (v)<-[:IsPublishedIn]-(all:Publication) // Get all papers of venue v 
    WITH v, related_papers, COUNT(DISTINCT all) as total_papers
    WHERE total_papers > 0 AND (related_papers * 1.0 / total_papers) >= {percentage}
    SET v:{get_community_venue_label(community)}                                // Tag this venue for this community        
    """
    run_query(tx, query)

# Get the top 100 papers of those community-venues that have any keyword
# related to the community. The strategy is to gather those with the maximum citation count
# Then, those top papers will be labeled as Top paper for that specific community (property)
def step3_recsys_rank_top100_papers(tx,     
    community: str = "Database",
    top_n: int = 100):
    
    query = f"""
    MATCH (k:KeyWord)<-[:HasKeyWord]-(p:Publication)-[:IsPublishedIn]->(v:{get_community_venue_label(community)})
    MATCH (citing:Publication)-[:Cites]->(p) // Get citations with keywords related to the community
    MATCH (k)<-[:HasKeyWord]-(c:Community {{name: "{community}"}})
    WITH p, COUNT(DISTINCT citing) AS citations
    ORDER BY citations DESC
    LIMIT {top_n}
    SET p:{get_community_toppaper_label(community)}
    """
    
    run_query(tx, query)

# Label the potential reviewers out of the top papers by 
def step4_recsys_label_reviewers_and_gurus(tx,
    community: str = "Database",
    min_guru_top_papers: int = 2):
        
    query = f"""
    MATCH (a:Author)-[:Wrote]->(p:{get_community_toppaper_label(community)})
    WITH a, COUNT(p) AS top_papers
    SET a: {get_community_reviewer_label(community)} // Recommend community reviewer
    WITH a, top_papers
    WHERE top_papers >= {min_guru_top_papers}
    SET a:{get_community_guru_label(community)} // Recommend gurus for that community
    
    """
    run_query(tx, query)

def undo_recsys_modifications(tx, steps: List[int] = [0,1,2,3,4], community: str = "Database"):
    undo_queries = {
        0: f"MATCH (c:Community {{name: '{community}'}})-[r:HasKeyWord]->() DELETE r, c",
        1: f"MATCH (v:{get_community_venue_label(community)}) REMOVE v",
        2: f"MATCH (p:{get_community_toppaper_label(community)}) REMOVE p",
        3: f"MATCH (a:{get_community_reviewer_label(community)}) REMOVE a",
        4: f"MATCH (a:{get_community_guru_label(community)}) REMOVE a:{get_community_guru_label(community)}",
    }

    for step in steps:
        query = undo_queries.get(step)
        if query:
            run_query(tx, query)

def execute_recommendation_algorithm(driver: GraphDatabase.driver = driver):
    with driver.session() as session:
        # All these operations are effectiely upserts
        if not args.rm:
            session.execute_write(step1_recsys_define_community)
            session.execute_write(step2_recsys_label_venues)
            session.execute_write(step3_recsys_rank_top100_papers)
            session.execute_write(step4_recsys_label_reviewers_and_gurus)
        else:
            session.execute_write(undo_recsys_modifications)
        
        


def parse_args():
    parser = argparse.ArgumentParser(description="Run recommendation system with optional preprocessing.")
    parser.add_argument(
        "--preprocess", 
        action="store_true", 
        help="Flag to indicate whether to run the preprocessing step (default is not to preprocess)"
    )
    parser.add_argument(
        "--recommend", 
        action="store_true", 
        help="Flag to indicate whether to run the recommendation algorithm (default is not to recommend)"
    )
    parser.add_argument(
        "--rm", 
        action="store_true", 
        help="Flag to indicate whether to first undo the recommendations of previous runs"
    )    
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()

    # PART 1: PREPROCESS KEYWORDS (only if --preprocess flag is set)
    if args.preprocess:
        papers = fetch_papers_from_neo4j()
        logger.success(f"Fetched {len(papers)} papers from Neo4J successfully!")
        papers_df = pd.DataFrame(papers)

        # YAKE is fast < 5s but updating the graph could take long
        max_ngram = 2
        num_keywords = 5
        dedupthreshold = 0.8

        preprocess_keywords_and_update_graph(
            papers_df,
            max_ngram=max_ngram,
            num_keywords=num_keywords,
            dedupthreshold=dedupthreshold,
        )
        logger.success(
            f"Extracted keywords from papers successfully! (Each paper with {num_keywords}, {max_ngram} max ngrams each, with a deduplication threshold of {dedupthreshold})"
        )

    if args.recommend:
        # PART 2: EXECUTE RECOMMENDATION ALGORITHM
        execute_recommendation_algorithm()
        logger.success(
            f"Successfully executed reviewer recommendation system, open your Neo4J browser to visualize results"
        )
        
