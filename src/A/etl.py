import pprint
import pandas 
import numpy
import json


##
## ETL process for preprocessing the data into a "schema" format
##


if __name__ == "__main__":
    with open("data/rel-2025-03-04-papers-01.jsonl", "r") as f:
        for line in f:
            paper = json.loads(line)
            pprint.pprint(paper)
            quit()
    print("ETL complete.")