#!/usr/bin/env python3
"""
OpenAlex literature search scaffold for Small Circles.

Fetches scholarly work metadata (title, year, DOI, abstract, authors, OA URL)
for CBT / mHealth / peer-support queries. Does NOT scrape publisher HTML or
paywalled full text.

Usage:
  python scripts/lit_search_openalex.py
  python scripts/lit_search_openalex.py --mailto you@example.com --limit 20
  python scripts/lit_search_openalex.py --queries scripts/lit_search_queries.json

Output:
  data/research/openalex_results.csv
  data/research/openalex_results.json

Then screen hits and capture design notes in:
  docs/cbt-informed-research.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUERIES = Path(__file__).resolve().parent / "lit_search_queries.json"
OUT_DIR = ROOT / "data" / "research"
USER_AGENT_TMPL = "SmallCirclesLitSearch/0.1 (mailto:{mailto})"

# Load config
def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)

# OpenAlex get
def openalex_get(url: str, mailto: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT_TMPL.format(mailto=mailto),
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Reconstruct abstract
def reconstruct_abstract(inverted: dict | None) -> str:
    """OpenAlex stores abstracts as inverted index; rebuild plain text."""
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in positions)

# Search works
# 1. Define filters, params, url
# 2. Get payload from OpenAlex
# 3. Process results
# 4. Append to results list
# 5. Break if limit reached
# 6. Return results
def search_works(
    *,
    query: str,
    mailto: str,
    limit: int,
    min_year: int | None,
) -> list[dict]:
    filters = ["type:article|review"]
    if min_year:
        filters.append(f"from_publication_date:{min_year}-01-01")

    params = {
        "search": query,
        "filter": ",".join(filters),
        "per_page": min(limit, 50),
        "sort": "relevance_score:desc",
        "mailto": mailto,
    }
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    payload = openalex_get(url, mailto)
    results: list[dict] = []
    for work in payload.get("results", []):
        authorships = work.get("authorships") or []
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in authorships[:8]
            if (a.get("author") or {}).get("display_name")
        ]
        primary = work.get("primary_location") or {}
        source = (primary.get("source") or {}).get("display_name", "")
        oa = work.get("open_access") or {}
        results.append(
            {
                "openalex_id": work.get("id", ""),
                "title": work.get("display_name") or work.get("title") or "",
                "year": work.get("publication_year") or "",
                "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
                "cited_by_count": work.get("cited_by_count") or 0,
                "authors": "; ".join(authors),
                "venue": source,
                "is_oa": bool(oa.get("is_oa")),
                "oa_url": oa.get("oa_url") or primary.get("landing_page_url") or "",
                "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
                "concepts": "; ".join(
                    c.get("display_name", "")
                    for c in (work.get("concepts") or [])[:8]
                    if c.get("display_name")
                ),
            }
        )
        if len(results) >= limit:
            break
    return results

# Write outputs to CSV and JSON, with screen decision and design notes
def write_outputs(rows: list[dict], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "openalex_results.csv"
    json_path = out_dir / "openalex_results.json"

    fieldnames = [
        "query_id",
        "query_label",
        "openalex_id",
        "title",
        "year",
        "doi",
        "cited_by_count",
        "authors",
        "venue",
        "is_oa",
        "oa_url",
        "concepts",
        "abstract",
        "screen_decision",
        "design_notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row.setdefault("screen_decision", "")  # include / maybe / exclude
            row.setdefault("design_notes", "")
            writer.writerow(row)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return csv_path, json_path

# Main function
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenAlex lit search for Small Circles")
    
    # Add queries - path to lit_search_queries.json
    parser.add_argument(
        "--queries",
        type=Path,
        default=DEFAULT_QUERIES,
        help="Path to lit_search_queries.json",
    )
    
    # Add mailto - contact email for OpenAlex polite pool (overrides JSON)
    parser.add_argument(
        "--mailto",
        default=None,
        help="Contact email for OpenAlex polite pool (overrides JSON)",
    )
    
    # Add limit - max results per query (overrides JSON)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max results per query (overrides JSON)",
    )
    
    # Add min_year - earliest publication year (overrides JSON)
    parser.add_argument(
        "--min-year",
        type=int,
        default=None,
        help="Earliest publication year (overrides JSON)",
    )
    
    # Add out - output directory
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR,
        help="Output directory",
    )
    
    # Parse arguments
    args = parser.parse_args(argv)

    # Load config
    config = load_config(args.queries)
    mailto = args.mailto or config.get("mailto") or "your-email@example.com"
    if "example.com" in mailto:
        print(
            "Warning: set a real --mailto or edit scripts/lit_search_queries.json "
            "(OpenAlex polite pool).",
            file=sys.stderr,
        )
    limit = args.limit if args.limit is not None else int(config.get("per_query_limit", 25))
    min_year = (
        args.min_year
        if args.min_year is not None
        else config.get("min_year")
    )

    all_rows: list[dict] = []
    seen_ids: set[str] = set()

    for q in config.get("queries", []):
        qid = q.get("id", "query")
        label = q.get("label", qid)
        search = q.get("search", "")
        print(f"Searching [{qid}] {label} ...")
        try:
            hits = search_works(
                query=search,
                mailto=mailto,
                limit=limit,
                min_year=int(min_year) if min_year else None,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {exc}", file=sys.stderr)
            continue

        added = 0
        for hit in hits:
            oid = hit.get("openalex_id") or hit.get("title")
            if oid in seen_ids:
                continue
            seen_ids.add(oid)
            hit["query_id"] = qid
            hit["query_label"] = label
            all_rows.append(hit)
            added += 1
        print(f"  kept {added} new works (fetched {len(hits)})")
        time.sleep(0.2)  # be polite

    # Write outputs
    csv_path, json_path = write_outputs(all_rows, args.out)
    print(f"Wrote {len(all_rows)} rows -> {csv_path}")
    print(f"Wrote JSON     -> {json_path}")
    print("Next: screen the CSV, then fill docs/cbt-informed-research.md")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
