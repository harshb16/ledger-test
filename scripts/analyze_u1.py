"""Analyze unchanged mock or live U1 outputs."""
import argparse
from ledger.u1 import analyze

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir')
    args = parser.parse_args()
    analyze(args.run_dir)
