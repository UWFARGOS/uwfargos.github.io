"""
sources.py — one adapter per applicant tracking system.

Every adapter returns a list of dicts with the same shape:
    {id, title, company, location, url, posted, description}

Greenhouse, Lever, Ashby and Workable serve plain unauthenticated GET JSON.
Workday needs a POST with a JSON body and blocks cross-origin browser calls,
which is why this pipeline runs server-side instead of in the page.
USAJOBS needs a free key from developer.usajobs.gov.
"""

import os
import re
import time
import html
from urllib.parse import urlparse

import requests

UA = "UWF-Argo-Internship-Board/1.0 (llong@uwf.edu)"
TIMEOUT = 25
PAUSE = 1.0  # be a polite citizen; these are free endpoints


def _clean(text):
    """Strip HTML tags and entities down to searchable plain text."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _get(url, **kw):
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json"},
                     timeout=TIMEOUT, **kw)
    r.raise_for_status()
    time.sleep(PAUSE)
    return r.json()


# ---------------------------------------------------------------------------

def greenhouse(emp):
    """token: the slug in boards.greenhouse.io/<token>"""
    token = emp["token"]
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"gh-{token}-{j['id']}",
            "title": j.get("title", ""),
            "company": emp["name"],
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "posted": j.get("updated_at", ""),
            "description": _clean(j.get("content", "")),
        })
    return out


def lever(emp):
    token = emp["token"]
    data = _get(f"https://api.lever.co/v0/postings/{token}?mode=json")
    out = []
    for j in data:
        out.append({
            "id": f"lv-{token}-{j.get('id')}",
            "title": j.get("text", ""),
            "company": emp["name"],
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "posted": j.get("createdAt", ""),
            "description": _clean(j.get("descriptionPlain") or j.get("description", "")),
        })
    return out


def ashby(emp):
    token = emp["token"]
    data = _get("https://api.ashbyhq.com/posting-api/job-board/"
                f"{token}?includeCompensation=true")
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"ab-{token}-{j.get('id')}",
            "title": j.get("title", ""),
            "company": emp["name"],
            "location": j.get("location", ""),
            "url": j.get("jobUrl", ""),
            "posted": j.get("publishedAt", ""),
            "description": _clean(j.get("descriptionHtml") or j.get("descriptionPlain", "")),
        })
    return out


def workable(emp):
    token = emp["token"]
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{token}?details=true")
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"wk-{token}-{j.get('shortcode')}",
            "title": j.get("title", ""),
            "company": emp["name"],
            "location": ", ".join(filter(None, [j.get("city"), j.get("state")])),
            "url": j.get("url", ""),
            "posted": j.get("published_on", ""),
            "description": _clean(j.get("description", "") + " " + j.get("requirements", "")),
        })
    return out


def parse_workday_url(url):
    """
    Turn a careers page URL into (tenant, dc, site).
    https://acme.wd5.myworkdayjobs.com/en-US/External  ->  ('acme','wd5','External')

    Derived rather than hand-typed because tenant slugs are easy to get wrong
    and the careers URL is the one thing you can always copy from a browser.
    """
    p = urlparse(url)
    host = p.netloc
    m = re.match(r"([^.]+)\.(wd\d+)\.myworkdayjobs\.com", host)
    if not m:
        raise ValueError(f"not a myworkdayjobs.com URL: {url}")
    tenant, dc = m.group(1), m.group(2)
    parts = [s for s in p.path.split("/") if s]
    parts = [s for s in parts if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", s)]
    if not parts:
        raise ValueError(f"no career site path in: {url}")
    return tenant, dc, parts[0]


def workday(emp, want_details=True, cap=400):
    """
    Workday's list response is thin, so full descriptions need a second call
    per posting. `cap` bounds that: enterprise tenants can have thousands of
    roles and you only need the ones a student could plausibly hold.

    `search` may be a single string or a list. A list runs one query per term
    and merges the results, which matters because a single "intern" query
    silently excludes every entry-level full-time role.
    """
    tenant, dc, site = parse_workday_url(emp["careers_url"])
    base = f"https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Content-Type": "application/json",
                         "Accept": "application/json"})

    terms = emp.get("search", "")
    if isinstance(terms, str):
        terms = [terms]
    if not terms:
        terms = [""]

    out, seen = [], set()

    for term in terms:
        offset, total = 0, None
        while offset < (total if total is not None else 1) and len(out) < cap:
            r = sess.post(f"{base}/jobs",
                          json={"appliedFacets": {}, "limit": 20,
                                "offset": offset, "searchText": term},
                          timeout=TIMEOUT)
            r.raise_for_status()
            payload = r.json()
            total = payload.get("total", 0)
            postings = payload.get("jobPostings", [])
            if not postings:
                break
            for j in postings:
                path = j.get("externalPath", "")
                if path in seen:
                    continue
                seen.add(path)
                out.append({
                    "id": f"wd-{tenant}-{j.get('bulletFields', [path])[0]}",
                    "title": j.get("title", ""),
                    "company": emp["name"],
                    "location": j.get("locationsText", ""),
                    "url": f"https://{tenant}.{dc}.myworkdayjobs.com/{site}{path}",
                    "posted": j.get("postedOn", ""),
                    "description": "",
                    "_path": path,
                })
            offset += 20
            time.sleep(PAUSE)

    if want_details:
        for job in out:
            try:
                d = sess.get(f"{base}{job.pop('_path')}", timeout=TIMEOUT).json()
                job["description"] = _clean(
                    (d.get("jobPostingInfo") or {}).get("jobDescription", ""))
                time.sleep(0.4)
            except Exception:
                job.pop("_path", None)
    else:
        for job in out:
            job.pop("_path", None)
    return out


def usajobs(emp):
    """
    Federal accounting and audit roles — heavily underused by students, and
    relevant given the Navy and DoD presence on the Gulf Coast.

    Needs USAJOBS_KEY and USAJOBS_EMAIL in the environment. The User-Agent
    header must be the email you registered with, not a browser string; that
    trips up almost everyone on their first call.
    """
    key, email = os.environ.get("USAJOBS_KEY"), os.environ.get("USAJOBS_EMAIL")
    if not (key and email):
        # Raise rather than return [], so the run report shows FAILED with a
        # reason. Returning an empty list made this look like "answered, but
        # nothing matched", which sent us chasing the wrong problem.
        raise RuntimeError(
            "USAJOBS_KEY / USAJOBS_EMAIL not set. Add them under "
            "Settings > Secrets and variables > Actions. Key is free from "
            "developer.usajobs.gov/apirequest")

    headers = {"Host": "data.usajobs.gov", "User-Agent": email,
               "Authorization-Key": key}

    # Only documented parameters, and never send an empty one — an empty
    # LocationName is not the same as omitting it and can zero out results.
    # HiringPath was dropped deliberately: it isn't in the documented
    # parameter set, and the text filter already screens for student and
    # entry-level roles far more reliably than a facet we're guessing at.
    base = {
        "JobCategoryCode": emp.get("series", "0510;0511;0501;1160"),
        "ResultsPerPage": 500,
    }
    if emp.get("location"):
        base["LocationName"] = emp["location"]
    if emp.get("keyword"):
        base["Keyword"] = emp["keyword"]

    out, page, pages = [], 1, 1
    while page <= pages and page <= 5:
        params = dict(base, Page=page)
        r = requests.get("https://data.usajobs.gov/api/search", headers=headers,
                         params=params, timeout=TIMEOUT)
        r.raise_for_status()
        result = r.json().get("SearchResult", {})
        items = result.get("SearchResultItems", [])
        if page == 1:
            total = int(result.get("SearchResultCountAll", 0) or 0)
            per = int(base["ResultsPerPage"])
            pages = max(1, -(-total // per)) if total else 1
            print(f"  USAJOBS: {total} announcements across {pages} page(s)")
        if not items:
            break

        for it in items:
            d = it.get("MatchedObjectDescriptor", {})
            ud = d.get("UserArea", {}).get("Details", {})
            out.append({
                "id": f"us-{d.get('PositionID')}",
                "title": d.get("PositionTitle", ""),
                "company": d.get("OrganizationName", "Federal Government"),
                "location": "; ".join(l.get("LocationName", "")
                                      for l in d.get("PositionLocation", [])[:5]),
                "url": d.get("PositionURI", ""),
                "posted": d.get("PublicationStartDate", ""),
                "description": _clean(" ".join([
                    d.get("QualificationSummary", ""),
                    ud.get("JobSummary", ""), ud.get("Requirements", ""),
                    ud.get("Education", "")])),
            })
        page += 1
        time.sleep(PAUSE)
    return out


def manual(emp):
    """
    Hand-maintained entries for employers with no public feed.

    The bulge brackets are the reason this exists. Goldman, Morgan Stanley and
    JPMorgan don't expose campus roles through any public API, and no amount of
    probing changes that. But a student still needs to know the program exists
    and roughly when it opens — arguably more than they need a live req count,
    since these cycles close in weeks.

    Entries carry an explicit level and bucket and skip the text filter, since
    there is no posting text to screen. They render on the board with a
    "Check directly" flag so nobody mistakes them for a live listing.
    """
    out = []
    for i, role in enumerate(emp.get("roles", []), 1):
        out.append({
            "id": f"mn-{emp['name'].lower().replace(' ', '-')}-{i}",
            "title": role["title"],
            "company": emp["name"],
            "location": role.get("location", ""),
            "url": role.get("url") or emp.get("url", ""),
            "posted": "",
            "description": role.get("note") or emp.get("note", ""),
            "_manual": True,
            "_level": role.get("level", "Internship"),
            "_bucket": role.get("bucket", "Investment Banking & Markets"),
            "_cycle": role.get("cycle", ""),
        })
    return out


ADAPTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workable": workable,
    "workday": workday,
    "usajobs": usajobs,
    "manual": manual,
}
