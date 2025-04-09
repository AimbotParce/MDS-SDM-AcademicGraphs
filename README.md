# MDS-SDM-AcademicGraphs
Create, visualize, modify and analyze the graphs created from academic papers.

## Installation

### To run the scripts manually

If you want to run the scripts manually, you'll need to install the following
dependencies:

- Python 3.10 or higher
- Neo4j 5.0 or higher (Or have access to a Neo4j instance)
- Neo4j Cypher Shell (Which is included in the Neo4j Desktop installation)

Then run the following command to install the required Python packages:

```sh
pip install -r requirements.txt
```

It is recommended to use a virtual environment to avoid conflicts with other
projects. Create one using the following command:

```sh
python -m venv venv
```

Then activate it using the following command:
- On Windows:
```sh
venv\Scripts\activate
```
- On Linux or MacOS:
```sh
source venv/bin/activate
```

### Using Docker

Alternatively, a Docker compose file is provided to automatically spin up a
Neo4j instance, and load sample data into it. To do so, make sure you have Docker
and Docker Compose installed.

## Usage

### Using Docker

A Docker compose file is provided. To use it, you first need to set up the
following environment variables:

- `NEO4J_USER`: The username for the Neo4j instance (you choose it)
- `NEO4J_PASSWORD`: The password for the Neo4j instance (you choose it)
- `S2_API_KEY`: An API key for the Semantic Scholar API (you can get one [here](https://www.semanticscholar.org/product/api))
- `S2_QUERY`: The query to use for the papers search using the Semantic Scholar API

You can also set the following optional environment variables:

- `S2_MIN_CITATIONS`: The minimum number of citations for the papers to be
  included in the graph (default: 1).
- `S2_PUBLICATION_YEAR`: The publication year of the papers to be included in
  the graph. It can be a single year or a range of years (default: 1900-9999).
- `S2_LIMIT`: The maximum number of papers to be included in the graph 
  (default: 100).
- `S2_MAX_RETRIES`: The maximum number of retries for the API requests (default:
   3).

Then, you can run the following command to start the Neo4j instance and load
the sample data into it:

```sh
docker-compose up -d
```

This docker image contains the installation of the "Graph Data Science (GDS)" Library, so its highly advisable to use the image for simplicity

**Note:** You can set up the environment variables in a `.env` file in the same
directory and instead use the command `docker-compose --env-file .env up -d`.

### Manually executing the scripts

If you want to run the scripts manually, we'll suppose that you have access to
a Neo4j instance. You can use the Neo4j Desktop application or a remote instance.

1. First, create a new database in your Neo4j instance.
2. Then, run the following command to download the data from the Semantic Scholar
   API:

    ```sh
    python3 src/download_academic.py "<your_query>" --output data/raw \
        --min-citations <min_citations> \
        --year <year_or_range> \
        --limit <limit>
    ```

    This will create two files in the `data/raw` directory:
    - `raw-papers-1.jsonl`: A JSONL file containing the papers data.
    - `raw-references-1.jsonl`: A JSONL file containing the citation data.
  
>[!WARNING]
>It is highly advisable to use the `--limit` option to avoid downloading too
>much data. Otherwise, you can add the `--batch-size` option to break the
>files into smaller chunks. By default, there is no batch size applied.
>Keep in mind that in that case, you'll have to modify the cypher loading
>script to load from all the files, not only the first one.

3. After that, run the following command to transform the raw data into a
    Neo4j-compatible format:

    ```sh
    python3 src/prepare.py data/raw/raw-papers-*.jsonl --output neo4j/import --type papers
    ```

    This will create a bunch of CSV files in the `neo4j/import` directory.
    Keep in mind that this directory **must be equal to your instance's import
    directory**, otherwise Neo4j won't be able to load the files. Thus, if you
    are using another installation of Neo4j other than the one provided by
    Docker, you must change the `neo4j/import` directory to your instance's
    import directory.

    Then, run the following command to transform the citations into a
    Neo4j-compatible format:

    ```sh
    python3 src/prepare.py data/raw/raw-references-1.jsonl --output neo4j/import --type references
    ```

    Again, this will create a bunch of CSV files in the `neo4j/import`
    directory, which must be equal to your instance's import directory.

4. Finally, run the following command to load the data into Neo4j:

    ```sh
    cypher-shell --address neo4j://<neo4j_hsot>:<neo4j_port> --username <your_user> \
        --password <your_password> --database <your_database> --file src/load_data.cyp
    ```

After that, you should be able to see the data in your Neo4j instance. You can
use the Neo4j Browser to visualize the graph and run queries on it.

### Execution Flags

In order to avoid repeated execution after downloading all papers one can set up the following flags to avoid download/import by using: 

```sh
touch neo4j/logs/neo4j-download.flag 
touch neo4j/logs/neo4j-import.flag
# To remove the flags
sudo rm neo4j/logs/*.flag 
```

## TO-DO list
Remaining tasks for the 1st delivery:
- [ ] script to create synthetic data
- [x] Neo4J data loading script
- [x] Improve the Docker compose for the automatic ingestion
- [ ] Check what is happening with the `IsPublishedIn` edges that go to empty nodes
- [ ] Do the "evolving the graph" A.3 section 
- [ ] Code the 4 queries in Cypher (2 for each member)
- [ ] Code the 4 recommending queries in Cypher (2 for each member)
- [ ] Implement the 2 graph algorithms using GDS library (1 for each member)
- [ ] Interpret the results (1 for each member)
- [ ] Write the final report overleaf (both)