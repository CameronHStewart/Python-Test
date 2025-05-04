#!/usr/bin/env python3
"""
web_frequencies.py
~~~~~~~~~~~~~~~~~~

Scrape a given web page, then report:

1. The top *N* most frequent words found in the visible text.
2. A count of each HTML tag used in the document.

Command‑line usage
------------------
$ python web_frequencies.py https://example.com --top 100

Positional arguments
--------------------
url                 Fully‑qualified URL to scrape.

Optional arguments
------------------
--top / -t N        How many words to display (default: 100).

Exit status
-----------
0   Successful run.
1   Network or HTTP error.
2   Invalid URL or parsing error.

Dependencies
------------
pip install requests beautifulsoup4 lxml

Notes & ethics
--------------
* Always respect a site’s robots.txt and terms of service.
* Excessive scraping can overwhelm servers; this script makes a single
  request only, but add delays or caching if batching URLs.
* For simplicity the stop‑word list is a minimal built‑in set; replace
  with a more comprehensive list (e.g. spaCy) if required.
"""

import argparse
import logging
import re
import sys
from collections import Counter
from html import unescape
from pathlib import Path
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# --------------------------- configuration -------------------------------- #

USER_AGENT = (
    "Mozilla/5.0 (compatible; WebFreqBot/1.0; +https://github.com/your-org)"
)
TIMEOUT = 10  # seconds
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "with",
}  # extend as needed

TOKEN_RE = re.compile(r"[A-Za-z]{2,}")  # two or more alphabetic characters

# ----------------------------- utilities ----------------------------------- #


def fetch_html(url: str) -> str:
    """Download HTML from *url* and return as Unicode text."""
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except (requests.RequestException, UnicodeDecodeError) as exc:
        logging.error("Failed to fetch %s: %s", url, exc)
        sys.exit(1)


def visible_text_from_soup(soup: BeautifulSoup) -> str:
    """
    Extract visible text from a BeautifulSoup tree.

    Invisible elements (scripts, styles, etc.) are removed before
    concatenation.
    """
    # Remove common non‑visible tags
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    # Generator for visible strings
    def gen() -> str:
        for element in soup.stripped_strings:
            # Skip comments and other non‑string Navigables
            if isinstance(element, NavigableString) and not isinstance(
                element, Tag
            ):
                yield unescape(element)

    return " ".join(gen())


def tokenise(text: str) -> List[str]:
    """
    Split *text* into lowercase tokens of alphabetic characters,
    excluding stop‑words.
    """
    tokens = (match.group(0).lower() for match in TOKEN_RE.finditer(text))
    return [tok for tok in tokens if tok not in STOP_WORDS]


def top_n_words(tokens: List[str], n: int) -> List[Tuple[str, int]]:
    """Return the *n* most common words and their counts."""
    return Counter(tokens).most_common(n)


def tag_frequencies(soup: BeautifulSoup) -> List[Tuple[str, int]]:
    """Return a frequency list of all HTML tag names (lower‑case)."""
    tags = (tag.name.lower() for tag in soup.find_all(True))
    return Counter(tags).most_common()


def render_report(
    url: str,
    word_counts: List[Tuple[str, int]],
    tag_counts: List[Tuple[str, int]],
) -> str:
    """Format the results into a human‑readable report."""
    lines: List[str] = []
    lines.append(f"Report for {url}")
    lines.append("=" * (len(lines[-1])))
    lines.append("")

    # Tag counts
    lines.append("HTML tag frequencies:")
    for tag, count in tag_counts:
        lines.append(f"  {tag:<15} {count:>6}")
    lines.append("")

    # Word counts
    lines.append(f"Top {len(word_counts)} words:")
    rank_width = len(str(len(word_counts)))
    for idx, (word, count) in enumerate(word_counts, 1):
        lines.append(f"  {idx:>{rank_width}d}. {word:<20} {count:>6}")
    lines.append("")
    return "\n".join(lines)


# ------------------------------ main logic --------------------------------- #


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command‑line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape a web page and analyse word/tag frequencies."
    )
    parser.add_argument("url", help="Fully‑qualified URL to scrape.")
    parser.add_argument(
        "-t",
        "--top",
        type=int,
        default=100,
        help="Number of most frequent words to show (default: 100).",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> None:
    """Entry point for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    args = parse_args(argv)

    logging.info("Fetching %s ...", args.url)
    html = fetch_html(args.url)
    soup = BeautifulSoup(html, "lxml")

    logging.info("Analysing HTML structure ...")
    tag_counts = tag_frequencies(soup)

    logging.info("Extracting and processing text ...")
    text = visible_text_from_soup(soup)
    tokens = tokenise(text)
    word_counts = top_n_words(tokens, args.top)

    report = render_report(args.url, word_counts, tag_counts)
    print(report)


if __name__ == "__main__":
    main(sys.argv[1:])
