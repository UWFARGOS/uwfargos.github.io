"""
fetch.py — pull every employer, filter, write site/jobs.json.

    python scripts/fetch.py                 # normal run
    python scripts/fetch.py --audit         # also write rejected.json
    python scripts/fetch.py --only Deloitte # one employer, for debugging

A failing employer never fails the run. Stale data beats a broken page, and
the summary at the end tells you what needs attention.
"""

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sources import ADAPTERS          # noqa: E402
from filters import classify          # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "jobs.json"


def load_employers():
    with open(ROOT / "employers.yaml") as f:
        return yaml.safe_load(f)["employers"]


def dedupe(jobs):
    """
    Same role posted to two boards, or one Workday req advertised in six
    cities. Collapse on company + normalised title, keeping the first.
    """
    seen, out = set(), []
    for j in jobs:
        key = (j["company"].lower().strip(),
               " ".join(j["title"].lower().split()))
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true",
                    help="write site/rejected.json so you can see what was filtered out")
    ap.add_argument("--only", help="run a single employer by name")
    ap.add_argument("--max-years", type=int, default=1,
                    help="reject postings demanding more than this many years")
    args = ap.parse_args()

    employers = load_employers()
    if args.only:
        employers = [e for e in employers
                     if args.only.lower() in e["name"].lower()]
        if not employers:
            sys.exit(f"no employer matching {args.only!r}")

    kept, rejected, report = [], [], []

    for emp in employers:
        adapter = ADAPTERS.get(emp["source"])
        if not adapter:
            report.append((emp["name"], "ERROR", f"unknown source {emp['source']}"))
            continue
        try:
            raw = adapter(emp)
        except Exception as exc:
            report.append((emp["name"], "FAILED", str(exc)[:80]))
            continue

        n_kept = 0
        for job in raw:
            job = classify(job, emp.get("kind", "other"), args.max_years)
            job["employer_kind"] = emp.get("kind", "other")
            if job.pop("keep"):
                job.pop("reject_reason", None)
                # Trim the description — the page shows a snippet and links out.
                job["snippet"] = job["description"][:280]
                job.pop("description")
                kept.append(job)
                n_kept += 1
            elif args.audit:
                rejected.append({"title": job["title"], "company": job["company"],
                                 "reason": job["reject_reason"]})
        report.append((emp["name"], "ok", f"{n_kept} kept of {len(raw)}"))

    kept = dedupe(kept)
    kept.sort(key=lambda j: (j.get("posted") or ""), reverse=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(kept),
        "jobs": kept,
    }, indent=1))

    if args.audit:
        (ROOT / "site" / "rejected.json").write_text(json.dumps(rejected, indent=1))

    print("\n" + "-" * 62)
    for name, status, detail in report:
        print(f"{status:<7} {name:<32} {detail}")
    print("-" * 62)
    print(f"{len(kept)} postings written to {OUT.relative_to(ROOT)}")
    failures = sum(1 for _, s, _ in report if s in ("FAILED", "ERROR"))
    if failures:
        print(f"{failures} employer(s) need attention — run scripts/verify.py")


if __name__ == "__main__":
    main()
