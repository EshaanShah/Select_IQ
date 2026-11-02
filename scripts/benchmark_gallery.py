#!/usr/bin/env python3
"""Benchmark entry point for Phase 0 and image-pipeline feasibility work."""

from argparse import ArgumentParser
from pathlib import Path


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("gallery", type=Path, help="Path to a permissioned local JPEG gallery")
    args = parser.parse_args()
    raise SystemExit(
        f"Benchmark scaffold is ready for US-04 implementation; no files were read from {args.gallery}."
    )


if __name__ == "__main__":
    main()

