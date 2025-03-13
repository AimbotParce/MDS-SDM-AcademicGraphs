import csv
import json
import pathlib
import pprint
from typing import List, Literal, Optional, TypedDict

from tqdm import tqdm


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

    id: str
    author_ids: List[str]
    open_access: bool
    journal: Optional[_Journal]
    publication_date: str
    venue_id: str
    fields_of_study: List[str]
    title: str
    url: str
    year: int
    embedding: List[float]
    tldr: str


class Author(TypedDict):
    id: str
    url: str
    name: str
    affiliations: List[str]
    homepage: str
    h_index: int


headers = {
    "venue": ["id", "name", "type", "alternate_names", "url"],
    "author": ["id", "name", "affiliations", "homepage", "url", "h_index"],
    "paper": [
        "id",
        "open_access",
        "publication_date",
        "title",
        "url",
        "year",
        "embedding",
        "tldr",
    ],
}

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
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        choices=headers.keys(),
        help="Type of file being loaded",
        required=True,
    )
    args = parser.parse_args()

    header: list[str] = headers[args.type]

    for input_file in args.input_files:
        output_file: pathlib.Path = args.output_dir / f"{input_file.stem}.csv"
        with (
            open(input_file, encoding="utf-8") as input_fd,
            open(output_file, "w", encoding="utf-8") as output_fd,
        ):
            writer = csv.writer(output_fd)
            # Write the header
            writer.writerow(header)
            for entry in tqdm(
                map(json.loads, input_fd),
                leave=False,
                desc=f"Parsing {input_file.name}",
                unit="rows",
            ):
                writer.writerow(map(entry.get, header))
            print(f"Loaded {input_file}!")
