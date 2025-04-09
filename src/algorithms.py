from neo4j import GraphDatabase
import pandas as pd
from dotenv import load_dotenv
import os
import json
from loguru import logger
from typing import List, Dict, Optional
import re
from pathlib import Path

load_dotenv()
neo4j_username = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
# Connect to Neo4j
driver = GraphDatabase.driver(
    "bolt://localhost:7687", auth=(neo4j_username, neo4j_password)
)


######
###### Reviewer recommendation (Cypher)
######


def run_query(tx, query):
    tx.run(query)

def to_camel_case(name: str) -> str:
    parts = re.split(r'[\s_-]+', name)
    return ''.join(word.capitalize() for word in parts) 

def run_pagerank(driver: GraphDatabase.driver, output_path: Optional[Path] = None):
    graph_name = "pageRankGraph"

    with driver.session() as session:
        # Drop graph if exists (GDS logic)
        exists_result = session.run(f"CALL gds.graph.exists('{graph_name}') YIELD exists")
        if exists_result.single()['exists']:
            session.run(f"CALL gds.graph.drop('{graph_name}') YIELD graphName")

        # Project citation graph of publications
        session.run(f"""
            CALL gds.graph.project(
                '{graph_name}',
                'Publication',
                {{
                    Cites: {{
                        orientation: 'REVERSE'
                    }}
                }}
            )
        """)

        # Run PageRank, here the query can be modified further
        result = session.run(f"""
            CALL gds.pageRank.stream('{graph_name}')
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).title AS title, score
            ORDER BY score DESC
        """)

        df = pd.DataFrame([r.data() for r in result])
        if output_path:
            df.to_csv(output_path / "pagerank.csv", index=False)

        return df

def run_nodesim_author_similarity(driver: GraphDatabase.driver, output_path: Optional[Path] = None):
    graph_name = "nodeSimilarity"

    with driver.session() as session:
        # Drop graph if it exists
        exists_result = session.run(f"CALL gds.graph.exists('{graph_name}') YIELD exists")
        if exists_result.single()['exists']:
            session.run(f"CALL gds.graph.drop('{graph_name}') YIELD graphName")

        # Project the graph using your actual node labels and relationship types
        session.run(f"""
            CALL gds.graph.project(
                '{graph_name}',
                ['Author', 'Publication'],
                ['Wrote', 'MainAuthor']
            )
        """)

        # Run node similarity
        result = session.run(f"""
            CALL gds.nodeSimilarity.stream('{graph_name}')
            YIELD node1, node2, similarity
            RETURN
                gds.util.asNode(node1).name AS author1,
                gds.util.asNode(node2).name AS author2,
                similarity
            ORDER BY similarity DESC, author1, author2
        """)

        df = pd.DataFrame([r.data() for r in result])
        if output_path:
            df.to_csv(output_path / "node_similarity.csv", index=False)

        return df

if __name__ == "__main__":
    pagerank = run_pagerank(driver=driver, output_path=Path("./datasets"))
    print(pagerank.head(10)) 
    nodesim = run_nodesim_author_similarity(driver=driver, output_path=Path("./datasets"))
    print(nodesim.head(10))