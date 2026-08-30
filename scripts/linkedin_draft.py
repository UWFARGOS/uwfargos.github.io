"""
linkedin_draft.py — turn new postings into a LinkedIn post you can paste.

    python scripts/linkedin_draft.py                # drafts from the last diff
    python scripts/linkedin_draft.py --bucket Tax   # one field only
    python scripts/linkedin_draft.py --deadline     # recruiting-clock post instead

This drafts. It does not post. LinkedIn's API is partner-gated and automated
posting through unofficial routes risks your account, so the output goes to
your clipboard and you press the button. That is also better content: a post
from you reads differently than a bot feed.

Run fetch.py first. It writes site/jobs.json; this compares against
site/.last_post.json to find what's new since you last drafted.
"""

import argparse
import json
import pathlib
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
JOBS = ROOT / "site" / "jobs.json"
SEEN = ROOT / "site" / ".last_post.json"
CALENDAR = ROOT / "site" / "calendar.json"
SITE_URL = "https://YOUR-USERNAME.github.io/argo-internships/"

LIMIT = 3000  # LinkedIn post character limit

# Unicode mathematical bold — survives LinkedIn's plain-text field.
_BOLD = {}
for a, b in ((0x41, 0x1D400), (0x61, 0x1D41A), (0x30, 0x1D7CE)):
    n = 26 if a != 0x30 else 10
    for i in range(n):
        _BOLD[chr(a + i)] = chr(b + i)


def bold(text):
    return "".join(_BOLD.get(c, c) for c in text)


def load_new(bucket=None, level=None):
    data = json.loads(JOBS.read_text())
    jobs = data.get("jobs", [])
    seen = set(json.loads(SEEN.read_text())) if SEEN.exists() else set()

    new = [j for j in jobs if j["id"] not in seen]
    if bucket:
        new = [j for j in new if bucket.lower() in (j.get("bucket") or "").lower()]
    if level:
        new = [j for j in new if j.get("level") == level]

    # Lead with the ones students most need to see.
    def priority(j):
        f = j.get("flags", [])
        return (0 if "Sophomore eligible" in f else 1,
                0 if j.get("level") == "Internship" else 1,
                j.get("company", ""))
    new.sort(key=priority)
    return new, jobs


def draft_roles(new, limit=8):
    if not new:
        return ("No new postings since your last draft. Run "
                "`python scripts/fetch.py` first, or use --deadline.")

    shown = new[:limit]
    head = f"{len(new)} new finance and accounting internships just opened."

    lines = [bold(head), ""]
    lines.append("Everything below is screened — no postings asking for "
                 "three years of experience, no senior titles hiding behind "
                 "an \"entry level\" tag.")
    lines.append("")

    for j in shown:
        tag = ""
        if "Sophomore eligible" in j.get("flags", []):
            tag = " (sophomores can apply)"
        elif "CPA track" in j.get("flags", []):
            tag = " (CPA track)"
        loc = f" — {j['location']}" if j.get("location") else ""
        lines.append(f"▸ {bold(j['title'])}, {j['company']}{loc}{tag}")

    if len(new) > limit:
        lines.append(f"\n...and {len(new) - limit} more on the board.")

    lines += [
        "",
        bold("One thing to keep in mind:"),
        "Finance recruits early. If you are a sophomore reading this and "
        "waiting for junior-year career fairs, you are already behind on "
        "several of these tracks.",
        "",
        f"Full board, updated daily: {SITE_URL}",
        "",
        "#Accounting #Finance #Internships #UWF",
    ]
    return "\n".join(lines)


def draft_deadline():
    """A recruiting-clock post. Higher value than a listings dump, and reusable."""
    cal = json.loads(CALENDAR.read_text())
    today = date.today()

    lines = [bold("Where finance recruiting actually stands right now."), "",
             "Students consistently underestimate how far ahead these cycles "
             "run. Here is the current state by track.", ""]

    for tr in cal["tracks"]:
        live = [w for w in tr["windows"] if w["status"] in ("open", "opening")]
        if not live:
            continue
        lines.append(bold(tr["track"]))
        for w in live:
            opens = date.fromisoformat(w["opens"])
            closes = date.fromisoformat(w["closes"])
            days = (closes - today).days
            if 0 < days < 120:
                detail = f"about {days} days left"
            elif opens > today:
                detail = f"opens {opens.strftime('%B %Y')}"
            else:
                detail = f"open through {closes.strftime('%B %Y')}"
            lines.append(f"▸ {w['cycle']} — {detail}")
        lines.append(f"  {tr['audience']}")
        lines.append("")

    lines += [f"Screened postings for each of these: {SITE_URL}", "",
              "#Accounting #Finance #Internships #CareerAdvice"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", help="limit to one field, e.g. Tax")
    ap.add_argument("--level", choices=["Internship", "Entry level"])
    ap.add_argument("--deadline", action="store_true",
                    help="draft a recruiting-clock post instead of a listings post")
    ap.add_argument("--mark-seen", action="store_true",
                    help="record these as posted so the next draft skips them")
    args = ap.parse_args()

    if args.deadline:
        text = draft_deadline()
        new, all_jobs = [], []
    else:
        new, all_jobs = load_new(args.bucket, args.level)
        text = draft_roles(new)

    print("=" * 64)
    print(text)
    print("=" * 64)
    n = len(text)
    status = "OK" if n <= LIMIT else f"OVER by {n - LIMIT} — trim it"
    print(f"{n} / {LIMIT} characters — {status}")

    if args.mark_seen and all_jobs:
        SEEN.write_text(json.dumps([j["id"] for j in all_jobs]))
        print(f"Marked {len(all_jobs)} postings as seen.")


if __name__ == "__main__":
    main()
