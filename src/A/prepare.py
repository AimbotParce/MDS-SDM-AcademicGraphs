import csv
import json
import pathlib

from tqdm import tqdm

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
