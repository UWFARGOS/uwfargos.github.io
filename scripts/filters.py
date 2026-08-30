"""
filters.py — eligibility screening and classification.

This is the part that makes the board useful. Generic job sites tag a role
"entry level" if the employer ticked a box, which is why "entry level" searches
return postings asking for five years of experience. Everything here works off
the actual posting text instead.

Edit the pattern lists freely. They are ordinary regexes and the tests in
tests_filters.py will tell you if you break something.
"""

import re
from datetime import date

# ---------------------------------------------------------------------------
# Inclusion signals
# ---------------------------------------------------------------------------

INTERN_TITLE = re.compile(
    r"\b(intern|internship|co-?op|summer analyst|summer associate|"
    r"summer scholar|trainee)\b", re.I)

ENTRY_TITLE = re.compile(
    r"\b(entry[- ]level|new grad(uate)?|campus hire|university (hire|graduate)|"
    r"graduate program|rotational|analyst i{1,2}\b|staff accountant|"
    r"associate accountant|audit associate|tax associate|assurance associate)\b",
    re.I)

# "Associate" alone is ambiguous. At a public accounting firm it is the
# entry-level campus title; at a bank it is a post-MBA hire. Resolved in
# classify() using the employer's `kind`.
BARE_ASSOCIATE = re.compile(r"\bassociate\b", re.I)

ENTRY_BODY = re.compile(
    r"\b(no prior experience|entry[- ]level|recent graduate|new graduate|"
    r"currently enrolled|pursuing a (bachelor|master)|undergraduate student|"
    r"rising (junior|senior|sophomore)|degree in progress)\b", re.I)

# ---------------------------------------------------------------------------
# Exclusion signals
# ---------------------------------------------------------------------------

# Seniority is judged on the TITLE only. A description can legitimately say
# "rising senior" or "reports to the senior manager" without the role being senior.
SENIOR_TITLE = re.compile(
    r"\b(senior|sr\.?|lead|principal|manager|mgr\.?|director|"
    r"vice president|vp\b|head of|chief|supervisor|controller|partner)\b", re.I)

# Years of experience. Only counts when "experience" appears within ~40 chars,
# so "within 2 years of graduation" and "150 hours" don't trigger it.
YEARS_EXP = re.compile(
    r"(\d{1,2})\s*(?:\+|or more|plus)?\s*(?:-|to|–)?\s*(\d{1,2})?\s*"
    r"\+?\s*years?.{0,40}?\bexperien", re.I | re.S)

CPA_REQUIRED = re.compile(
    r"\b(licensed cpa|cpa (license|certification) (is )?required|"
    r"active cpa|must (be a|hold a[n]? active) cpa|cpa required)\b", re.I)

CPA_TRACK = re.compile(
    r"\b(cpa[- ]eligible|cpa track|working toward.{0,20}cpa|"
    r"150 (semester )?(credit )?hours?|150-hour)\b", re.I)

CLEARANCE = re.compile(
    r"\b(active (security )?clearance|ts/sci|top secret|"
    r"secret clearance|public trust)\b", re.I)

NO_SPONSORSHIP = re.compile(
    r"\b(not (able to )?(provide|offer|sponsor)|will not sponsor|"
    r"no (visa )?sponsorship|unable to sponsor)\b", re.I)

SOPHOMORE_OK = re.compile(
    r"\b(freshman|first[- ]year student|sophomore|rising sophomore|"
    r"early identification|early insight|discover|explore program|"
    r"launch (internship|program)|pipeline program|pre[- ]internship)\b", re.I)

REMOTE = re.compile(r"\b(remote|work from home|virtual|telework)\b", re.I)

GRAD_YEAR = re.compile(r"\b(?:class of|graduat\w+\s+(?:in|by)?)\s*(20\d{2})\b", re.I)

# ---------------------------------------------------------------------------
# Location — US only
# ---------------------------------------------------------------------------
# Several large employers run a single global Workday tenant, so a fetch pulls
# reqs from Toronto, London and Bangalore alongside Tampa. Filtering here is
# more reliable than trying to use Workday's location facets, whose IDs differ
# per tenant.

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico", "GU": "Guam",
    "VI": "US Virgin Islands",
}
_NAME_TO_CODE = {v.lower(): k for k, v in US_STATES.items()}

# Two-letter codes must be matched case-sensitively and on a word boundary.
# "IN" would otherwise match the word "in" in every location string.
_STATE_CODE = re.compile(r"\b(" + "|".join(US_STATES) + r")\b")
_STATE_NAME = re.compile(r"\b(" + "|".join(re.escape(n) for n in _NAME_TO_CODE)
                         + r")\b", re.I)

US_MARKER = re.compile(r"\b(united states|u\.?s\.?a?\.?|usa)\b", re.I)

# Country and city names, matched case-insensitively.
NON_US_NAME = re.compile(
    r"\b(canada|canadian|ontario|quebec|british columbia|alberta|manitoba|"
    r"saskatchewan|nova scotia|newfoundland|toronto|vancouver|montreal|"
    r"calgary|ottawa|edmonton|winnipeg|halifax|"
    r"united kingdom|u\.k\.|england|scotland|wales|ireland|london|dublin|"
    r"manchester|glasgow|edinburgh|belfast|leeds|bristol|cardiff|"
    r"germany|france|spain|italy|netherlands|belgium|poland|switzerland|"
    r"sweden|norway|denmark|finland|portugal|austria|czech|romania|hungary|"
    r"greece|luxembourg|frankfurt|munich|berlin|hamburg|paris|madrid|"
    r"barcelona|milan|rome|amsterdam|brussels|zurich|geneva|warsaw|prague|"
    r"stockholm|copenhagen|oslo|helsinki|lisbon|vienna|budapest|"
    r"india|china|japan|korea|singapore|australia|new zealand|philippines|"
    r"malaysia|indonesia|thailand|vietnam|taiwan|hong kong|israel|"
    r"mexico|brazil|argentina|chile|colombia|peru|south africa|egypt|nigeria|"
    r"bangalore|bengaluru|mumbai|delhi|hyderabad|chennai|pune|gurgaon|noida|"
    r"kolkata|shanghai|beijing|shenzhen|tokyo|osaka|seoul|sydney|melbourne|"
    r"brisbane|perth|auckland|manila|dubai|abu dhabi|riyadh|doha|"
    r"emea|apac|latam|europe|european|asia pacific|middle east)\b", re.I)

# Two-letter codes must be case-sensitive: lowercase "on", "in", "ab" appear
# constantly in ordinary text. No Canadian code collides with a US state code.
NON_US_CODE = re.compile(r"\b(ON|QC|BC|AB|MB|SK|NS|NB|NL|PE|YT|NT|NU|UK|GB)\b")

AMBIGUOUS_LOC = re.compile(
    r"\b(multiple locations|various|remote|virtual|anywhere|flexible|nationwide)\b",
    re.I)


def us_location(loc):
    """
    Classify a location string.

    Returns (verdict, state_code) where verdict is True (US), False (not US),
    or None (can't tell). Ambiguous ones are kept but flagged rather than
    thrown away — "Multiple Locations" on a US tenant is usually US offices,
    and silently dropping those loses good postings.
    """
    loc = (loc or "").strip()
    if not loc:
        return None, None

    # A US signal anywhere wins, even in a mixed multi-city string, because
    # a req listing "Chicago, IL; Toronto, ON" is open to a US student.
    m = _STATE_CODE.search(loc)
    if m:
        return True, m.group(1)
    m = _STATE_NAME.search(loc)
    if m:
        return True, _NAME_TO_CODE[m.group(1).lower()]
    if US_MARKER.search(loc):
        return True, None

    if NON_US_NAME.search(loc) or NON_US_CODE.search(loc):
        return False, None
    if AMBIGUOUS_LOC.search(loc):
        return None, None
    return None, None

# ---------------------------------------------------------------------------
# Buckets — the categories students actually think in
# ---------------------------------------------------------------------------

BUCKETS = [
    ("Audit & Assurance", r"\b(audit|assurance|attest|internal audit|soc [12])\b"),
    ("Tax", r"\b(tax|state and local|salt\b|transfer pricing)\b"),
    ("Advisory & Consulting", r"\b(advisory|consulting|transaction services|"
                              r"valuation|forensic|risk advisory|deal)\b"),
    ("Corporate FP&A", r"\b(fp&a|financial planning (and|&) analysis|"
                       r"financial analyst|budget analyst|cost accounting|"
                       r"corporate finance)\b"),
    ("Accounting Operations", r"\b(staff accountant|general ledger|accounts "
                              r"payable|accounts receivable|payroll|"
                              r"revenue accounting|controller|bookkeep)\b"),
    ("Commercial & Credit", r"\b(credit|commercial bank|underwrit|"
                            r"loan|lending|portfolio manager)\b"),
    ("Treasury", r"\b(treasury|cash management|liquidity|capital markets)\b"),
    ("Wealth & Financial Planning", r"\b(wealth|financial plan|advisor|"
                                    r"private client|retirement|cfp\b)\b"),
    ("Insurance & Actuarial", r"\b(actuar|insurance|claims|underwriting)\b"),
    ("Investment Banking & Markets", r"\b(investment bank|m&a|equity research|"
                                     r"sales and trading|leveraged finance)\b"),
]
BUCKETS = [(name, re.compile(pat, re.I)) for name, pat in BUCKETS]


def _min_years(text):
    """Largest minimum-years requirement stated in the posting, or 0."""
    worst = 0
    for m in YEARS_EXP.finditer(text or ""):
        try:
            worst = max(worst, int(m.group(1)))
        except (TypeError, ValueError):
            continue
    return worst


def classify(job, employer_kind="other", max_years=1, us_only=True,
             keep_ambiguous_location=True):
    """
    Decide whether a posting belongs on the board and tag it.

    Returns the job dict with `keep`, `reject_reason`, `level`, `bucket`,
    `state` and `flags` added. Nothing is silently dropped — rejects keep
    their reason so you can audit what the filter is throwing away.
    """
    title = job.get("title", "") or ""
    body = job.get("description", "") or ""
    blob = f"{title}\n{body}"

    job["flags"] = flags = []
    job["bucket"] = None
    job["level"] = None
    job["state"] = None

    # --- location ----------------------------------------------------------
    # Checked first: it's the cheapest test and rejects the most postings
    # when an employer runs a single global career site.
    if us_only:
        verdict, state = us_location(job.get("location"))
        job["state"] = state
        if verdict is False:
            job["keep"] = False
            job["reject_reason"] = f"outside the US ({job.get('location','')})"
            return job
        if verdict is None:
            if not keep_ambiguous_location:
                job["keep"] = False
                job["reject_reason"] = f"location unclear ({job.get('location','')})"
                return job
            flags.append("Check location")

    # --- level -------------------------------------------------------------
    if INTERN_TITLE.search(title):
        job["level"] = "Internship"
    elif ENTRY_TITLE.search(title):
        job["level"] = "Entry level"
    elif BARE_ASSOCIATE.search(title) and employer_kind == "accounting":
        # "Audit Associate" at a CPA firm is the campus hire title.
        job["level"] = "Entry level"
    elif SOPHOMORE_OK.search(title) or SOPHOMORE_OK.search(body):
        # Early-ID and pipeline programs rarely say "intern" anywhere. They are
        # the most realistic entry point for a non-target student, so they get
        # their own path in rather than falling through.
        job["level"] = "Internship"
    elif INTERN_TITLE.search(body) and ENTRY_BODY.search(body):
        job["level"] = "Internship"
    elif ENTRY_BODY.search(body):
        job["level"] = "Entry level"

    if not job["level"]:
        job["keep"] = False
        job["reject_reason"] = "no internship or entry-level signal"
        return job

    # --- hard exclusions ---------------------------------------------------
    if SENIOR_TITLE.search(title):
        job["keep"] = False
        job["reject_reason"] = "senior title"
        return job

    years = _min_years(blob)
    if years > max_years:
        job["keep"] = False
        job["reject_reason"] = f"requires {years}+ years experience"
        return job

    if CPA_REQUIRED.search(blob):
        job["keep"] = False
        job["reject_reason"] = "active CPA license required"
        return job

    # --- flags -------------------------------------------------------------
    if CPA_TRACK.search(blob):
        flags.append("CPA track")
    if SOPHOMORE_OK.search(blob):
        flags.append("Sophomore eligible")
    if CLEARANCE.search(blob):
        flags.append("Clearance needed")
    if NO_SPONSORSHIP.search(blob):
        flags.append("No sponsorship")
    if REMOTE.search(f"{title} {job.get('location','')}"):
        flags.append("Remote")

    years_found = GRAD_YEAR.findall(blob)
    if years_found:
        job["grad_years"] = sorted({int(y) for y in years_found
                                    if date.today().year <= int(y) <= date.today().year + 5})

    # --- bucket ------------------------------------------------------------
    for name, pat in BUCKETS:
        if pat.search(title):
            job["bucket"] = name
            break
    else:
        for name, pat in BUCKETS:
            if pat.search(body):
                job["bucket"] = name
                break
    job["bucket"] = job["bucket"] or "General Finance & Accounting"

    job["keep"] = True
    job["reject_reason"] = None
    return job
