import yake
from neo4j import GraphDatabase
import pandas as pd
from dotenv import load_dotenv
import os
import json
from loguru import logger

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
            MERGE (k:Keyword {name: $keyword})
            WITH k  // Use WITH to pass `k` to the next part of the query
            MATCH (p:Publication {paperID: $paper_id})
            MERGE (p)-[:HasKeyword]->(k)
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
                session.write_transaction(insert_keywords, paper_id, keywords)


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


def step1_recsys_define_community(tx):
    query = """
    
    """
    run_query(tx, query)


def step2_recsys_label_venues(tx):
    query = """
    
    """
    run_query(tx, query)


def step3_recsys_rank_top100_papers(tx):
    query = """
    
    """
    run_query(tx, query)


def step4_recsys_label_reviewers_and_gurus(tx):
    query = """
    
    """
    run_query(tx, query)


def execute_recommendation_algorithm(driver: GraphDatabase.driver = driver):
    with driver.session() as session:
        # All these operations are effectiely upserts
        session.execute_write(step1_recsys_define_community)
        session.execute_write(step2_recsys_label_venues)
        session.execute_write(step3_recsys_rank_top100_papers)
        session.execute_write(step4_recsys_label_reviewers_and_gurus)


if __name__ == "__main__":

    # PART 1: PREPROCESS KEYWORDS
    papers = fetch_papers_from_neo4j()
    logger.success(f"Fetched {len(papers)} papers from Neo4J sucessfully!")
    papers_df = pd.DataFrame(papers)

    # YAKE is fast < 5s but updating the graph could tak elong
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

    # PART 2: EXECUTE RECOMMENDATION ALGORITHM
    execute_recommendation_algorithm()
