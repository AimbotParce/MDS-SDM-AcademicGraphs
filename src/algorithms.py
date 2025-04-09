import os
from pathlib import Path

import pandas as pd
from loguru import logger

from neo4j import Driver, GraphDatabase

######
###### Reviewer recommendation (Cypher)
######
PUBLICATION_PAGERANK_CREATE_PROJECTION = (
    "MATCH (dest:Publication) "
    "OPTIONAL MATCH (source:Publication)-[e:Cites]->(dest) "
    "RETURN gds.graph.project('{graph_name}', dest, source)"
)
PAGERANK_EXECUTE = (
    "CALL gds.pageRank.stream('{graph_name}') "
    "YIELD nodeId, score "
    "RETURN gds.util.asNode(nodeId).title AS title, score "
    "ORDER BY score DESC"
)
PUBLICATION_SIM_CREATE_PROJECTION = (
    "MATCH (dest:Publication) "
    "OPTIONAL MATCH (source:Publication|Author)-[e:Cites|Wrote]->(dest) "
    "RETURN gds.graph.project('{graph_name}', dest, source)"
)
NODESIM_EXECUTE = (
    "CALL gds.nodeSimilarity.stream('{graph_name}') "
    "YIELD node1, node2, similarity "
    "WITH gds.util.asNode(node1) AS node1, gds.util.asNode(node2) AS node2, similarity "
    "WHERE LABELS(node1)=['Publication'] AND LABELS(node2)=['Publication'] "
    "RETURN node1.title AS paper1, node2.title AS paper2, similarity "
    "ORDER BY similarity DESC, paper1, paper2"
)


def gds_delete_graph(driver: Driver, graph_name: str):
    """
    Delete a GDS graph if it exists.

    Args:
        driver (Driver): Neo4j driver.
        graph_name (str): Name of the graph to delete.
    """
    with driver.session() as session:
        exists_result = session.run(f"CALL gds.graph.exists('{graph_name}') YIELD exists")
        if exists_result.single()["exists"]:
            session.run(f"CALL gds.graph.drop('{graph_name}') YIELD graphName")
            logger.info(f"Graph {graph_name} dropped.")
        else:
            logger.info(f"Graph {graph_name} does not exist.")


def run_pagerank(driver: Driver) -> pd.DataFrame:
    """
    Run PageRank algorithm on the citation graph of publications.

    Args:
        driver (Driver): Neo4j driver.

    Returns:
        pd.DataFrame: DataFrame containing the PageRank scores of publications.
    """
    graph_name = "PageRankGraph"
    gds_delete_graph(driver, graph_name)

    with driver.session() as session:
        # Project citation graph of publications
        session.run(PUBLICATION_PAGERANK_CREATE_PROJECTION.format(graph_name=graph_name))

        # Run PageRank, here the query can be modified further
        result = session.run(PAGERANK_EXECUTE.format(graph_name=graph_name))

        res = pd.DataFrame([r.data() for r in result])
    gds_delete_graph(driver, graph_name)
    return res


def run_nodesim_author_similarity(driver: Driver):
    """
    Run Node Similarity algorithm on the author-publication graph.

    Args:
        driver (Driver): Neo4j driver.

    Returns:
        pd.DataFrame: DataFrame containing the node similarity scores of authors.
    """
    graph_name = "NodeSimilarityGraph"
    gds_delete_graph(driver, graph_name)

    with driver.session() as session:
        # Project the graph using your actual node labels and relationship types
        session.run(PUBLICATION_SIM_CREATE_PROJECTION.format(graph_name=graph_name))

        # Run node similarity
        result = session.run(NODESIM_EXECUTE.format(graph_name=graph_name))

        res = pd.DataFrame([r.data() for r in result])

    gds_delete_graph(driver, graph_name)
    return res


if __name__ == "__main__":
    neo4j_username = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    # Connect to Neo4j
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=(neo4j_username, neo4j_password))

    pagerank = run_pagerank(driver=driver)
    pagerank.to_csv(Path("./datasets") / "pagerank.csv", index=False)
    print(pagerank.head(10))
    nodesim = run_nodesim_author_similarity(driver=driver)
    nodesim.to_csv(Path("./datasets") / "node_similarity.csv", index=False)
    print(nodesim.head(10))
