"""The public pages of the website, with the title and description each one carries in search results.

Each description is the page's own opening line, and the site map lists exactly these pages.
Copied on 17 October 2026 from apps/web/lib/pages.ts. How it works, About and Questions were removed on
21 October 2026, and their addresses redirect (routes/system.py). Reporting and complaints was added the same day,
with the legal pack.
"""

PUBLIC_PAGES = {
    "home": {
        "path": "/",
        "title": "IkonetU | Connecting student founders to investors",
        "description": "Record a one-minute pitch, add your proof, and let investors ask to meet you.",
    },
    "founders": {
        "path": "/for-founders",
        "title": "For founders",
        "description": "Record a one-minute pitch, upload proof one piece at a time, and show up when investors search your sector, stage and country.",
    },
    "investors": {
        "path": "/for-investors",
        "title": "For investors",
        "description": "Search student founders by sector, stage, country and evidence, watch their pitches, and ask for an introduction.",
    },
    "trust": {
        "path": "/trust-and-safety",
        "title": "Trust and safety",
        "description": "IkonetU explains how it verifies evidence, who sees what, what the IkonetU Score is and how to raise a concern.",
    },
    "readiness": {
        "path": "/readiness-check",
        "title": "Readiness self-check",
        "description": "Answer eleven questions, one for each area of the IkonetU Score, and see what to add first. You need no account, and nothing is saved.",
    },
    "pricing": {
        "path": "/pricing",
        "title": "Pricing",
        "description": "Founders and investors each have two plans. Free covers the pitch, search and introductions, and Premium adds verification.",
    },
    "privacy": {
        "path": "/privacy",
        "title": "Privacy policy",
        "description": "How IkonetU Technology Limited collects, uses, shares and keeps personal data, and the rights you have. This version is dated 21 October 2026.",
    },
    "terms": {
        "path": "/terms",
        "title": "Terms",
        "description": "The terms of use, founder terms, investor terms, acceptable use policy and investment risk warning of IkonetU. This version is dated 21 October 2026.",
    },
    "cookies": {
        "path": "/cookies",
        "title": "Cookie policy",
        "description": "Every cookie and item of browser storage that IkonetU uses, what each one does and how long it lasts. This version is dated 21 October 2026.",
    },
    "complaints": {
        "path": "/complaints",
        "title": "Reporting and complaints",
        "description": "How to report content or a user on IkonetU, how to ask for a decision to be reviewed and how to complain. This policy is dated 21 October 2026.",
    },
}
