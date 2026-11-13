"""Run full population scenarios serially, releasing each process's caches."""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--reuse-existing-baseline", action="store_true")
    parser.add_argument(
        "--amounts", type=float, nargs="+", default=[0, 1, 10, 100, 1000, 10000]
    )
    args = parser.parse_args()
    worker = [sys.executable, "-u", "population_search.py", "--year", str(args.year)]
    if args.reuse_existing_baseline:
        assert Path("private_outputs/baseline.pkl").exists()
    else:
        subprocess.run(worker + ["--baseline-only"], check=True)
    for amount in args.amounts:
        subprocess.run(
            worker + ["--reuse-baseline", "--amounts", str(amount)], check=True
        )


if __name__ == "__main__":
    main()
