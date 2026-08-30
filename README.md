# Argo Internship Board

A curated internship and entry-level job board for finance and accounting
students. No server, no database, no student accounts. A scheduled script
pulls postings from employer applicant tracking systems, screens them, and
writes a JSON file that a static page reads.

## Why it's different from a generic job site

1. **"Entry level" is verified, not trusted.** Every posting is screened
   against its own text. A role asking for 3+ years, holding a senior title,
   or requiring an active CPA license is rejected regardless of how the
   employer categorized it.
2. **Curated employers.** Roughly 20 firms that actually hire regional
   accounting and finance graduates, not everything on the internet.
3. **A recruiting clock.** Finance recruits up to 18 months out. The page
   shows each track's application window against today's date, which is the
   single thing students most reliably don't know.

## Setup

```bash
git clone <your-repo>
cd argo-internships
pip install -r requirements.txt

# Free, instant key from https://developer.usajobs.gov/apirequest
export USAJOBS_KEY=...
export USAJOBS_EMAIL=you@uwf.edu

python scripts/verify.py      # DO THIS FIRST — see below
python scripts/fetch.py --audit
python -m http.server -d site 8000
```

### Verify before you trust it

**The employer tokens in `employers.yaml` are unverified seeds.** They were
written without network access, ATS slugs change, and some of these firms may
be on a platform with no public feed at all. `scripts/verify.py` makes one
cheap call per employer and tells you which entries resolve and how to fix the
ones that don't. Expect to fix several on the first pass. That's a one-time
half hour, and after that the list is stable.

Firms on iCIMS, Paycom, or Taleo have no public JSON feed. Don't fight it —
keep those in a short hand-maintained list and link out to their careers page.

## Tuning the filter

`scripts/filters.py` is the part worth your attention; everything else is
plumbing. It's plain regex lists with a test suite:

```bash
cd scripts && python tests_filters.py
```

Add a case to `tests_filters.py` whenever you spot a posting the filter got
wrong, then fix the pattern until it passes. That's how the board gets better
over a semester instead of drifting.

`python scripts/fetch.py --audit` writes `site/rejected.json` with a reason
per rejected posting. Read it occasionally — the filter throwing away good
roles is a quieter failure than letting bad ones through.

## Writing guides

Posts live as markdown files in `content/`. To publish one you don't need a
terminal at all:

1. On GitHub, open the `content` folder → **Add file** → **Create new file**
2. Name it something like `technical-interview-questions.md`
3. Copy the front matter block from `content/draft-template.md`, write below it
4. **Commit changes**

The Action rebuilds and publishes within about a minute. The filename becomes
the URL. Anything with `draft` in the filename is skipped, so you can leave
half-finished pieces in the folder.

## Deploying

Push to GitHub, then Settings → Pages → Source: **GitHub Actions**. Add
`USAJOBS_KEY` and `USAJOBS_EMAIL` under Settings → Secrets → Actions. The
workflow refreshes four times daily and redeploys. Free, and nothing to
maintain between semesters.

## Deliberate non-features

- **No student accounts, no saved applications, no logins.** The moment you
  store student data you've invited an IT security review and a FERPA
  conversation. Keep it read-only and anonymous.
- **No LinkedIn or Indeed scraping.** Against their terms, and you'd be
  IP-blocked within a week anyway.
- **No application submission.** Students apply on the employer's own site.

## Before launch

Talk to Career Services. UWF is almost certainly on Handshake, and this lands
far better as a complement — curated, screened, timeline-aware — than as a
shadow system. The same conversation covers using UWF marks or a uwf.edu
subdomain.

## Layout

```
employers.yaml          curated list — this is the product
site/index.html         the whole front end, one file
site/calendar.json      recruiting windows; review each August
site/jobs.json          generated output
scripts/filters.py      screening and classification
scripts/sources.py      one adapter per ATS
scripts/fetch.py        orchestrator
scripts/verify.py       employer list health check
scripts/tests_filters.py
scripts/build_posts.py  markdown -> published guides
scripts/linkedin_draft.py
content/*.md            your guides, written in markdown
site/learn.html         guides index
```

## Weekly rhythm

The Action handles postings on its own. A realistic weekly check is:

1. Open the Actions tab — is the latest run green?
2. Skim `site/rejected.json` for good roles the filter dropped
3. `python scripts/linkedin_draft.py --deadline` for a post to share
4. Add a guide if you have one

Nothing here is urgent. If you skip a week the site keeps refreshing.
