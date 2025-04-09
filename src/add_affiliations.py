import os
from typing import List

from loguru import logger

from lib.semantic_scholar import S2GraphAPI
from neo4j import GraphDatabase

AUTHOR_IDS_QUERY = "MATCH (a:Author) RETURN a.authorID AS authorID"
INSERT_QUERY = (
    'MATCH (a:Author {{authorID: "{author_id}"}}) '
    'MERGE (a)-[:IsAffiliatedWith]->(o:Organization {{name: "{affiliation}"}})'
)


def main(args):
    neo4j = GraphDatabase.driver(
        os.getenv("NEO4J_URL", "neo4j://localhost:7687"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
    )
    api = S2GraphAPI(api_key=os.getenv("S2_API_KEY"), default_max_retries=args.max_retries)

    total_affiliations = 0
    authors_with_affiliations = 0

    with neo4j.session() as session:
        # Find all the authors in the database
        result = session.run(AUTHOR_IDS_QUERY)
        author_ids: List[str] = [record["authorID"] for record in result]
        logger.info(f"Found {len(author_ids)} authors in the database")
        # Get the author details from the API
        for details in api.bulk_retrieve_author_details(author_ids, fields=["affiliations"], stream=True):
            if details is None:
                logger.warning("No details found for author")
                continue
            author_id = details["authorId"]
            affiliations: List[str] = details["affiliations"]
            if len(affiliations) > 0:
                authors_with_affiliations += 1
            total_affiliations += len(affiliations)
            for affiliation in affiliations:
                if not args.dry_run:
                    session.run(INSERT_QUERY.format(author_id=author_id, affiliation=affiliation))

    logger.success(f"Found {total_affiliations} affiliations for {len(author_ids)} authors")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Add affiliations to authors")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of retries for API requests")
    parser.add_argument("--dry-run", action="store_true", help="Don't download anything")
    args = parser.parse_args()

    main(args)
