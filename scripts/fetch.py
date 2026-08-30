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
import re
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
    cities. Collapse only true duplicates, and merge the multi-city case into
    a single entry carrying every location, so one req in forty cities shows
    as one row that is searchable by all forty.

    The earlier version keyed on company + title alone, which silently threw
    away every city after the first.
    """
    groups = {}
    for j in jobs:
        key = (j["company"].lower().strip(),
               " ".join(j["title"].lower().split()))
        if key not in groups:
            j["locations"] = []
            j["states"] = []
            groups[key] = j
        g = groups[key]

        for loc in re.split(r"\s*;\s*", (j.get("location") or "").strip()):
            loc = loc.strip()
            if loc and loc not in g["locations"]:
                g["locations"].append(loc)
        if j.get("state") and j["state"] not in g["states"]:
            g["states"].append(j["state"])

        # Prefer the flags of whichever copy carries the most information.
        if len(j.get("flags", [])) > len(g.get("flags", [])):
            g["flags"] = j["flags"]

    out = []
    for g in groups.values():
        locs = g["locations"]
        g["location"] = locs[0] if locs else ""
        g["extra_locations"] = max(0, len(locs) - 1)
        g["state"] = g["states"][0] if g["states"] else None
        out.append(g)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true",
                    help="write site/rejected.json so you can see what was filtered out")
    ap.add_argument("--only", help="run a single employer by name")
    ap.add_argument("--max-years", type=int, default=1,
                    help="reject postings demanding more than this many years")
    ap.add_argument("--allow-non-us", action="store_true",
                    help="keep postings outside the US (off by default)")
    ap.add_argument("--strict-location", action="store_true",
                    help="also drop postings whose location is unclear, e.g. "
                         "'Multiple Locations' or bare 'Remote'")
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
            job = classify(job, emp.get("kind", "other"), args.max_years,
                           us_only=not args.allow_non_us,
                           keep_ambiguous_location=not args.strict_location)
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

    print("\n" + "=" * 68)
    print(f"{'EMPLOYER':<32} {'STATUS':<9} DETAIL")
    print("-" * 68)
    for name, status, detail in report:
        print(f"{name:<32} {status:<9} {detail}")
    print("=" * 68)

    working = [r for r in report if r[1] == "ok" and "0 kept" not in r[2]]
    empty = [r for r in report if r[1] == "ok" and "0 kept" in r[2]]
    broken = [r for r in report if r[1] in ("FAILED", "ERROR")]

    print(f"{len(kept)} postings written to {OUT.relative_to(ROOT)}")
    if not args.allow_non_us:
        states = sorted({s for j in kept for s in (j.get("states") or [])})
        print(f"US states represented: {', '.join(states) if states else 'none yet'}")

    print(f"\n{len(working)} employer(s) produced postings, "
          f"{len(empty)} returned nothing, {len(broken)} failed outright.")

    if broken:
        print("\nFAILED — these are almost always a wrong careers_url or token:")
        for name, _, detail in broken:
            print(f"  · {name}: {detail}")
    if empty:
        print("\nRETURNED NOTHING — the endpoint answered but nothing survived "
              "the filter. Usually a career site with no campus roles posted, "
              "or a search term that matches nothing there:")
        for name, _, detail in empty:
            print(f"  · {name}: {detail}")
    if len(working) <= 2 and len(report) > 3:
        print("\n!! Almost every employer is failing. Fix employers.yaml before "
              "trusting anything on the site. Run the 'Check employer list' "
              "workflow to see what each one needs.")


if __name__ == "__main__":
    main()
