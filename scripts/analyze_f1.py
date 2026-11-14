"""Frozen follow-up analysis."""
import argparse
from ledger.f1 import analyze

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    analyze(parser.parse_args().run_dir)
