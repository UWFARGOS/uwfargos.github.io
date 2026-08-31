"""
discover.py — find the correct Workday URL for an employer.

    python scripts/discover.py deloittecareers
    python scripts/discover.py pwc kpmg ey rsmus

Why this works: Workday's error codes distinguish the two failure modes.

    422 Unprocessable Entity -> the tenant or the wdN data-centre number is
                                wrong; the request never reached a real tenant
    404 Not Found            -> tenant and data centre are RIGHT, but the
                                career-site path is wrong
    200 OK                   -> everything is correct

So we probe in two cheap phases: sweep the data-centre numbers with a
throwaway site name until one returns 404 instead of 422 (that pins the data
centre), then try candidate site names against it. Roughly 25 requests per
employer instead of the 135 a brute-force grid would need.

The heuristic above is inferred from observed behaviour, not documented by
Workday, so treat a clean 200 as the only real confirmation — which is what
this script reports.
"""

import argparse
import sys
import time

import requests

UA = "UWF-Argo-Internship-Board/1.0 (llong@uwf.edu)"
TIMEOUT = 15

DATA_CENTRES = ["wd1", "wd2", "wd3", "wd5", "wd10", "wd12",
                "wd101", "wd103", "wd105"]

# Ordered roughly by how often they turn up in the wild.
SITE_TEMPLATES = [
    "External", "ExternalCareers", "External_Career_Site", "Careers",
    "{t}Careers", "{t}_Careers", "{T}_External_Career_Site",
    "{t}_External", "Global_Careers", "GlobalCareers",
    "Campus", "CampusCareers", "Campus_Careers", "US_Campus",
    "Experienced", "Professional", "Search", "careers",
]

SENTINEL = "ZzNotARealCareerSite"


def _post(session, tenant, dc, site):
    url = (f"https://{tenant}.{dc}.myworkdayjobs.com"
           f"/wday/cxs/{tenant}/{site}/jobs")
    try:
        r = session.post(url, json={"appliedFacets": {}, "limit": 1,
                                    "offset": 0, "searchText": ""},
                         timeout=TIMEOUT)
        return r.status_code, r
    except requests.RequestException as exc:
        return None, exc


def find_data_centre(session, tenant):
    """Sweep wdN until one answers 404 (real tenant) rather than 422."""
    for dc in DATA_CENTRES:
        code, _ = _post(session, tenant, dc, SENTINEL)
        if code == 404:
            print(f"    {dc}: 404 -> tenant exists here")
            return dc
        if code == 200:
            print(f"    {dc}: 200 on sentinel (unexpected) -> treating as live")
            return dc
        print(f"    {dc}: {code}")
        time.sleep(0.3)
    return None


def find_site(session, tenant, dc):
    """Try candidate site names against the confirmed data centre."""
    tried = []
    for tpl in SITE_TEMPLATES:
        site = tpl.format(t=tenant, T=tenant.upper())
        if site in tried:
            continue
        tried.append(site)
        code, r = _post(session, tenant, dc, site)
        if code == 200:
            try:
                total = r.json().get("total", "?")
            except Exception:
                total = "?"
            print(f"    {site}: 200  ({total} postings)")
            return site, total
        time.sleep(0.3)
    return None, None


def discover(tenant):
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Content-Type": "application/json",
                            "Accept": "application/json"})

    print(f"\n{'=' * 62}\n{tenant}\n{'=' * 62}")
    print("  phase 1 — locating data centre")
    dc = find_data_centre(session, tenant)
    if not dc:
        print(f"  NOT FOUND. Every data centre returned 422, which means "
              f"'{tenant}' is not a real Workday tenant name.\n"
              f"  Open the firm's careers page, click any job, and read the "
              f"tenant from the address bar: https://TENANT.wdN.myworkdayjobs.com/...")
        return None

    print("  phase 2 — locating career site")
    site, total = find_site(session, tenant, dc)
    if not site:
        print(f"  Tenant found at {dc}, but none of the common site names "
              f"matched. Get the exact path from the careers page URL: the "
              f"segment right after the language code.")
        return None

    url = f"https://{tenant}.{dc}.myworkdayjobs.com/en-US/{site}"
    print(f"\n  WORKING — paste this into employers.yaml:\n")
    print(f"    careers_url: {url}")
    return url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tenants", nargs="+",
                    help="tenant guesses, e.g. pwc kpmg deloittecareers")
    args = ap.parse_args()

    found = {}
    for t in args.tenants:
        try:
            url = discover(t.strip())
            if url:
                found[t] = url
        except KeyboardInterrupt:
            sys.exit(1)

    print(f"\n{'=' * 62}\nSUMMARY: {len(found)} of {len(args.tenants)} resolved")
    for t, url in found.items():
        print(f"  {t}: {url}")
    if len(found) < len(args.tenants):
        print("\nFor the rest, the tenant name itself is wrong. There is no "
              "way around opening the careers page and reading it.")


if __name__ == "__main__":
    main()
