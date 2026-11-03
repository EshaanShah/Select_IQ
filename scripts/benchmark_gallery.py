#!/usr/bin/env python3
"""Benchmark entry point for Phase 0 and image-pipeline feasibility work."""

import hashlib
from argparse import ArgumentParser
from pathlib import Path
from time import perf_counter

from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.model_adapters import OpenClipVisualEncoder


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("gallery", type=Path, help="Path to a permissioned local JPEG gallery")
    parser.add_argument("--cache", type=Path, default=Path("var/cache"))
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    paths = sorted([*args.gallery.glob("*.jpg"), *args.gallery.glob("*.jpeg")])
    if not paths:
        raise SystemExit(f"No JPEG files found in {args.gallery}")
    encoder = OpenClipVisualEncoder("ViT-B-32", "laion2b_s34b_b79k")
    cache = NumpyEmbeddingCache(args.cache)

    for run in ("cold", "cached"):
        started = perf_counter()
        hits = 0
        misses: list[tuple[Path, Path]] = []
        for path in paths:
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            artifact = cache.image_path(encoder.fingerprint, content_hash)
            if cache.load(artifact, encoder.dimension) is not None:
                hits += 1
            else:
                misses.append((path, artifact))
        for offset in range(0, len(misses), args.batch_size):
            batch = misses[offset : offset + args.batch_size]
            vectors = encoder.encode_images([item[0] for item in batch])
            for (_, artifact), vector in zip(batch, vectors, strict=True):
                cache.save(artifact, vector)
        elapsed = perf_counter() - started
        print(
            f"{run}: photos={len(paths)} hits={hits} misses={len(misses)} "
            f"seconds={elapsed:.2f} device={encoder.device} dimension={encoder.dimension}"
        )


if __name__ == "__main__":
    main()

