import csv
import json
import os
from io import TextIOBase
from pathlib import Path
from typing import List

from tqdm import tqdm

from lib.models import *


def yieldFromFiles(files: List[Path]):
    for file in files:
        with open(file, "r") as f:
            yield from map(json.loads, f)


class BatchedWriter(TextIOBase):
    def __init__(self, file: os.PathLike, batch_size: int):
        self.file = str(file)
        # Check whether file has the "{batch}" placeholder
        if "{batch}" not in self.file:
            raise ValueError("File must have the '{batch}' placeholder")
        self.batch_size = batch_size

        self.batch_number = 1
        self.current_batch_size = 0
        self.output_file = open(self.file.format(batch=self.batch_number), "w")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.output_file.close()

    def write(self, line: str):
        if self.current_batch_size >= self.batch_size:
            self.output_file.close()
            self.batch_number += 1
            self.current_batch_size = 0
            self.output_file = open(self.file.format(batch=self.batch_number), "w")
        self.output_file.write(line)
        self.current_batch_size += 1

    def writelines(self, lines: List[str]):
        for line in lines:
            self.write(line)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare the Semantic Scholar dataset")
    parser.add_argument(
        "input_files",
        type=Path,
        nargs="+",
        help="Input JSONL files to prepare",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory to write the prepared dataset batches to",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        choices=["papers", "citations"],
        help="Type of file being loaded",
        required=True,
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size to write the prepared dataset",
    )
    args = parser.parse_args()

    input_files: list[Path] = args.input_files
    batch_size: int = args.batch_size
    file_type: str = args.type
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if file_type == "citations":
        with BatchedWriter(output_dir / "citations-{batch}.csv", batch_size) as output_file:
            writer = csv.DictWriter(
                output_file, fieldnames=["citedPaperID", "citingPaperID", "isInfluential", "contextsWithIntent"]
            )
            writer.writeheader()
            for citation in tqdm(yieldFromFiles(input_files), desc="Preparing Citations"):
                writer.writerow(
                    {
                        "citedPaperID": citation.get("citedPaper", {}).get("paperId"),
                        "citingPaperID": citation.get("citingPaper", {}).get("paperId"),
                        "isInfluential": citation.get("isInfluential", False),
                        "contextsWithIntent": json.dumps(citation["contextsWithIntent"]),
                    }
                )
    elif file_type == "papers":
        raise NotImplementedError("Preparing papers is not yet implemented")
    else:
        raise ValueError(f"Unknown file type: {file_type}")
