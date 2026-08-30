"""Run: python scripts/tests_filters.py"""
from filters import classify

CASES = [
    # (title, description, employer_kind, should_keep, note)
    ("Audit Intern - Summer 2027",
     "Currently enrolled in a Bachelor's or Master's in Accounting. 150 semester hours preferred.",
     "accounting", True, "classic Big 4 intern"),

    ("Audit Associate",
     "Entry-level role for recent graduates. CPA-eligible candidates preferred.",
     "accounting", True, "associate = entry level at CPA firms"),

    ("Associate, Investment Banking",
     "MBA required. 3+ years of prior banking experience.",
     "bank", False, "post-MBA associate must be excluded"),

    ("Financial Analyst",
     "Seeking a candidate with 5+ years of experience in corporate FP&A.",
     "corporate", False, "fake entry level"),

    ("Staff Accountant",
     "Recent graduate welcome. Requires 1 year of experience or internship.",
     "corporate", True, "1 year is acceptable"),

    ("Senior Tax Accountant",
     "Entry-level responsibilities in a growing team.",
     "accounting", False, "senior title beats body text"),

    ("Tax Intern",
     "Must be a licensed CPA.",
     "accounting", False, "CPA license required"),

    ("Summer Analyst - Credit",
     "Open to rising juniors and rising seniors. We will not sponsor visas.",
     "bank", True, "'rising senior' must not trip the seniority filter"),

    ("Early Insight Program - Sophomore",
     "Our early identification program for first-year students and sophomores.",
     "bank", True, "sophomore pipeline program"),

    ("Financial Planning Intern",
     "Support advisors with retirement and wealth planning. Recent graduate track.",
     "wealth", True, "wealth bucket"),

    ("Accountant",
     "Candidates must relocate within 2 years of hire. Entry-level position.",
     "corporate", True, "'within 2 years' is not an experience requirement"),

    ("Audit Manager",
     "Lead engagement teams.",
     "accounting", False, "manager"),
]


def main():
    fails = 0
    for title, desc, kind, expect, note in CASES:
        job = classify({"title": title, "description": desc, "location": "Pensacola, FL"}, kind)
        ok = job["keep"] == expect
        if not ok:
            fails += 1
        mark = "PASS" if ok else "FAIL"
        detail = job["reject_reason"] or f'{job["level"]} / {job["bucket"]} / {job["flags"]}'
        print(f"[{mark}] {title:<38} {detail}")
        if not ok:
            print(f"       ^ expected keep={expect} — {note}")
    print(f"\n{len(CASES) - fails}/{len(CASES)} passed")
    return fails


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
