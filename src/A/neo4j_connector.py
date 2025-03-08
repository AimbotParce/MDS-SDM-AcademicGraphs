from neo4j import GraphDatabase
from loguru import logger

class Neo4jConnector:
    
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri 
        self.user = user 
        self.password = password
        self.driver = None 
        self.connect()
        
    def connect(self, suicide_if_fail: bool = False):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.success(f"Sucessfully connected to Neo4J")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            if suicide_if_fail: 
                exit(-420)
                
    def close(self):
        if self.driver:
            self.driver.close()
            logger.success("Sucessfully disconnected from Neo4J")
    
    def query(self, query: str, params = None):
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return None
        
    def load_csv(self, csv_file, query):
        load_csv_query = f"""
            LOAD CSV WITH HEADERS FROM 'file:///{csv_file}' AS row
            {query}
            """
        self.run_query(load_csv_query)
        logger.succes(f"CSV file '{csv_file}' loaded successfully.")
        
if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()
    uri = os.getenv("NEO4J_URL", "bolt://localhost:7687")    
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your_password")

    connector = Neo4jConnector(uri, user, password)

    # Example: Load CSV data into Neo4j
    load_papers_query = """
    CREATE (:Paper {paperId: row.paperId, title: row.title, year: toInteger(row.year), abstract: row.abstract})
    """
    connector.load_csv('papers.csv', load_papers_query)
    connector.close()