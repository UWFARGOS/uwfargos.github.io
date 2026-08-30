"""
verify.py — check every employer entry actually resolves.

    python scripts/verify.py

Run this after editing employers.yaml and before trusting a fetch. It makes
one cheap call per employer and tells you exactly how to fix the broken ones.
"""

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sources import ADAPTERS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

HINTS = {
    "greenhouse": "Open the firm's careers page. If the URL is "
                  "boards.greenhouse.io/<slug> or the apply button goes there, "
                  "<slug> is your token.",
    "lever": "Look for jobs.lever.co/<slug>.",
    "ashby": "Look for jobs.ashbyhq.com/<slug>.",
    "workable": "Look for apply.workable.com/<slug>.",
    "workday": "Open the careers page and copy the full URL from the address "
               "bar. It must contain .myworkdayjobs.com. If it doesn't, the "
               "employer isn't on Workday — check for Greenhouse or move them "
               "to manual.yaml.",
    "usajobs": "Set USAJOBS_KEY and USAJOBS_EMAIL. The key is free and instant "
               "from developer.usajobs.gov/apirequest.",
}


def main():
    employers = yaml.safe_load((ROOT / "employers.yaml").read_text())["employers"]
    good = bad = 0

    for emp in employers:
        name, src = emp["name"], emp["source"]
        adapter = ADAPTERS.get(src)
        if not adapter:
            print(f"BROKEN  {name}: unknown source {src!r}")
            bad += 1
            continue
        try:
            if src == "workday":
                jobs = adapter(emp, want_details=False, cap=20)
            else:
                jobs = adapter(emp)
            print(f"OK      {name:<34} {len(jobs)} postings visible")
            good += 1
        except Exception as exc:
            print(f"BROKEN  {name:<34} {type(exc).__name__}: {str(exc)[:60]}")
            print(f"        fix: {HINTS.get(src, '')}")
            bad += 1

    print(f"\n{good} working, {bad} need fixing")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
