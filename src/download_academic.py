import json
import os
from argparse import ArgumentParser
from pathlib import Path

from loguru import logger

from lib.io import BatchedWriter
from lib.semantic_scholar import S2AcademicAPI


def main(args):
    connector = S2AcademicAPI(api_key=os.getenv("S2_API_KEY"), default_max_retries=3)

    if args.dry_run:
        logger.info("Running in DRY RUN mode. No data will be saved.")

    # Step 1: Retrieve Papers (4 in this case)
    papers = connector.bulk_retrieve_papers(
        args.query,
        minCitationCount=args.min_citations,
        year=args.year,
        fieldsOfStudy=args.fields,
        stream=True,
        limit=args.limit,
        sort="citationCount:desc",
    )
    paper_ids: list[str] = list(paper["paperId"] for paper in papers)
    logger.success(f"Retrieved {len(paper_ids)} papers.")
    del papers  # Free up memory

    logger.info("Retrieving paper details...")
    missing_fields = (
        "paperId",
        "embedding",
        "tldr",
        "url",
        "title",
        "abstract",
        "year",
        "isOpenAccess",
        "openAccessPdf",
        "publicationTypes",
        # Author fields
        "authors.authorId",
        "authors.url",
        "authors.name",
        "authors.affiliations",
        "authors.homepage",
        "authors.hIndex",
        # Field of study fields
        "fieldsOfStudy",
        # Publication venue or journal
        "journal",
        "publicationVenue",
        # If the paper is published in a Journal, "journal" has the information about the page number and things
        # about the journal. Also, publicationVenue might have some extra information about it.
        # If it is published in the Proceedings of a conference, "publicationVenue" has the information about the
        # conference and "journal" might have some extra information about where in the proceedings the paper is.
    )
    paper_details = connector.bulk_retrieve_details(paper_ids, missing_fields, batch_size=500)
    if not args.dry_run:
        with BatchedWriter(args.output / "raw-papers-{batch}.jsonl", batch_size=args.batch_size) as writer:
            for i, paper in enumerate(paper_details, start=1):
                writer.write(json.dumps(paper, ensure_ascii=False) + "\n")
            logger.success(f"Stored {i} paper details.")
    else:
        for i, paper in enumerate(paper_details, start=1):
            pass
        logger.success(f"Retrieved {i} paper details.")

    # Get all the citations
    logger.info("Retrieving citations...")
    citation_fields = "citingPaper.paperId", "isInfluential", "contextsWithIntent"
    citations = connector.bulk_retrieve_citations(paper_ids, citation_fields, stream=True)
    if not args.dry_run:
        with BatchedWriter(args.output / "raw-citations-{batch}.jsonl", batch_size=args.batch_size) as writer:
            for i, citation in enumerate(citations, start=1):
                writer.write(json.dumps(citation, ensure_ascii=False) + "\n")
            logger.success(f"Stored {i} citations.")
    else:
        for i, citation in enumerate(citations, start=1):
            pass
        logger.success(f"Retrieved {i} citations.")


if __name__ == "__main__":
    parser = ArgumentParser(description="Academic Paper Data Retrieval")
    parser.add_argument("query", type=str, help="Query to search for")
    parser.add_argument("--min-citations", type=int, default=None, help="Minimum number of citations")
    parser.add_argument(
        "--year", type=str, help="Year of publication (YYYY | YYYY-YYYY | YYYY- | -YYYY)", default=None
    )
    parser.add_argument("--fields", type=str, help="Fields of study to filter by", nargs="*", default=None)
    parser.add_argument("--output", type=Path, help="Output folder", default=None)
    parser.add_argument("--limit", type=int, help="Limit the number of papers to retrieve", default=None)
    parser.add_argument("--batch-size", type=int, help="Batch size for retrieving details", default=10000)
    parser.add_argument("--dry-run", action="store_true", help="Run without saving any data")
    args = parser.parse_args()
    if not args.dry_run and not args.output:
        parser.error("--output is required when not running in dry-run mode.")
    main(args)
