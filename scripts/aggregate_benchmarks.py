"""Aggregate AgentGuard benchmark JSON/JSONL files into Markdown."""

from __future__ import annotations

import argparse
from pathlib import Path

from agentguard.benchmarks import read_results, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="JSON or JSONL result files")
    parser.add_argument("--output", "-o", type=Path, help="write Markdown to this path")
    args = parser.parse_args()
    results = [result for path in args.inputs for result in read_results(path)]
    markdown = render_markdown(results)
    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
