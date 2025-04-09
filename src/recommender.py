import argparse
import os
import re
from typing import List

from loguru import logger

from neo4j import Driver, GraphDatabase


def run_query(tx, query):
    tx.run(query)


def to_camel_case(name: str) -> str:
    parts = re.split(r"[\s_-]+", name)
    return "".join(word.capitalize() for word in parts)


# Encapsulate LABEL logic in these functions to avoid hardcoding and low locality of behaviour
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
def step1_recsys_define_community(
    tx,
    community: str = "Database",
    keywords: List[str] = [
        "data management",
        "indexing",
        "data modeling",
        "big data",
        "data processing",
        "data storage",
        "data querying",
    ],
) -> None:

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
def step2_recsys_label_venues(tx, community: str = "Database", percentage: float = 0.001):

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
def step3_recsys_rank_top100_papers(tx, community: str = "Database", top_n: int = 100):

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
def step4_recsys_label_reviewers_and_gurus(tx, community: str = "Database", min_guru_top_papers: int = 2):

    query = f"""
    MATCH (a:Author)-[:Wrote]->(p:{get_community_toppaper_label(community)})
    WITH a, COUNT(p) AS top_papers
    SET a: {get_community_reviewer_label(community)} // Recommend community reviewer
    WITH a, top_papers
    WHERE top_papers >= {min_guru_top_papers}
    SET a:{get_community_guru_label(community)} // Recommend gurus for that community
    
    """
    run_query(tx, query)


def undo_recsys_modifications(tx, steps: List[int] = [0, 1, 2, 3, 4], community: str = "Database"):
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


def execute_recommendation_algorithm(driver: Driver):
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
        "--rm", action="store_true", help="Flag to indicate whether to first undo the recommendations of previous runs"
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URL", "neo4j://localhost:7687"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
    )

    # PART 2: EXECUTE RECOMMENDATION ALGORITHM
    execute_recommendation_algorithm(driver)
    logger.success(
        f"Successfully executed reviewer recommendation system, open your Neo4J browser to visualize results"
    )
    driver.close()
