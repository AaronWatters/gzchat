"""Simple add example module with CLI support."""

from __future__ import annotations

import argparse
from typing import Sequence


def add_numbers(first: int, second: int) -> int:
    """Return the sum of two integers."""
    return first + second


def main(argv: Sequence[str] | None = None) -> int:
    """Run the add_example command line interface."""
    parser = argparse.ArgumentParser(description="Add two numbers")
    parser.add_argument("first", type=int)
    parser.add_argument("second", type=int)
    args = parser.parse_args(argv)
    print(add_numbers(args.first, args.second))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
