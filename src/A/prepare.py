import json
import pathlib
import pprint


class Venue(TypedDict):
    id: str
    name: str
    type: Literal["conference", "journal"]
    alternate_names: List[str]
    url: str


class Paper(TypedDict):
    class _Journal(TypedDict):
        name: str
        volume: int
        pages: str

    corpus_id: int
    author_ids: List[str]
    open_access: bool
    journal: Optional[_Journal]
    publication_date: str
    venue_id: str
    fields_of_study: List[str]
    title: str
    url: str
    venue: str
    year: int
    embedding: List[float]
    tldr: str


class Author(TypedDict):
    author_id: str
    url: str
    name: str
    affiliations: List[str]
    homepage: str
    h_index: int


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare the Semantic Scholar dataset")
    parser.add_argument(
        "input_files",
        type=pathlib.Path,
        nargs="+",
        help="Input JSONL files to prepare",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=pathlib.Path,
        help="Output directory to write the prepared dataset batches to",
        required=True,
    )
    args = parser.parse_args()

    for input_file in args.input_files:
        output_file: pathlib.Path = args.output_dir / f"{input_file.stem}.csv"
        with (
            open(input_file, encoding="utf-8") as papers_file,
            open(output_file, "w", encoding="utf-8") as output_file,
        ):

            for line in papers_file:
                paper: Paper = json.loads(line)
                output_file.write(
                    paper["title"],
                    paper["corpusid"],
                    paper["isopenaccess"],
                    paper["publicationdate"],
                    paper["url"],
                    paper["year"],
                )

                pprint.pprint(paper)

                quit()

from typing import List, Literal, Optional, TypedDict
