"""Run the whole project end to end:  python run_pipeline.py [--from STEP] [--only STEP]

Steps (in order): download, harmonise, validate, build_db, descriptives, models, robustness, dashboard, memo, build_site
"""
import argparse
import importlib
import sys
import time

STEPS = ["download", "harmonise", "validate", "build_db", "descriptives", "models", "robustness", "dashboard", "memo",
         "build_site"]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--from", dest="start", choices=STEPS, default=STEPS[0], help="start at this step")
    p.add_argument("--only", choices=STEPS, help="run a single step")
    args = p.parse_args()
    steps = [args.only] if args.only else STEPS[STEPS.index(args.start):]
    for step in steps:
        t0 = time.time()
        print(f"\n===== {step} =====", flush=True)
        result = importlib.import_module(f"src.{step}").main()
        if step == "validate" and result != 0:
            print("Validation failed - stopping.")
            return 1
        print(f"----- {step} done in {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
