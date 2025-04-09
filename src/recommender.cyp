MERGE (c:Community {name: "Database"})
WITH c, [
  "data management", "indexing", "data modeling",
  "big data", "data processing", "data storage", "data querying"
] AS keywords
UNWIND keywords AS kw
MERGE (k:Keyword {name: kw})
MERGE (c)-[:HAS_KEYWORD]->(k)
