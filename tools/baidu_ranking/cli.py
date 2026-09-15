from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import RankingConfig, run_queries, write_reports


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local-only Baidu PC ranking query tool")
    parser.add_argument("--keyword", action="append", help="Keyword to query; repeat for batch mode")
    parser.add_argument("--keywords-file", type=Path, help="UTF-8 file with one keyword per line")
    parser.add_argument("--domain", help="Override BAIDU_RANKING_DOMAIN")
    parser.add_argument("--output-dir", default="artifacts/baidu-ranking", help="Local report directory")
    parser.add_argument("--format", choices=("json", "markdown", "both"), default="both")
    parser.add_argument("--batch", action="store_true", help="Explicitly confirm a multi-keyword run")
    parser.add_argument("--no-write", action="store_true", help="Print JSON to stdout without writing report files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = RankingConfig(domain=args.domain or RankingConfig().domain)
    keywords = list(args.keyword or [])
    if args.keywords_file:
        keywords.extend(line.strip() for line in args.keywords_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#"))
    if not keywords:
        keywords = config.keywords
    if len(keywords) > 1 and not args.batch:
        print("batch_confirmation_required: add --batch for more than one keyword", file=sys.stderr)
        return 2
    try:
        results = run_queries(config, keywords, batch=args.batch)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.no_write:
        print(json.dumps({"results": [result.to_dict() for result in results]}, ensure_ascii=False, indent=2))
    else:
        formats = {"json", "markdown"} if args.format == "both" else {args.format}
        for path in write_reports(results, args.output_dir, formats=formats):
            print(path)
    return 0 if all(result.status in {"ranked", "not_found"} for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
