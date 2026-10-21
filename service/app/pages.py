"""The public pages of the website, with the title and description each one carries in search results.

Each description is the page's own opening line, and the site map lists exactly these pages.
Copied on 17 October 2026 from apps/web/lib/pages.ts. How it works, About and Questions were removed on
21 October 2026, and their addresses redirect (routes/system.py).
"""

PUBLIC_PAGES = {
    "home": {
        "path": "/",
        "title": "IkonetU | Connecting early-stage founders to investors",
        "description": "Record a one-minute pitch and upload your proof. IkonetU reviewers check it against the source, and investors can ask to meet you.",
    },
    "founders": {
        "path": "/for-founders",
        "title": "For founders",
        "description": "Record a one-minute pitch, upload proof one piece at a time, and show up when investors search your sector, stage and country.",
    },
    "investors": {
        "path": "/for-investors",
        "title": "For investors",
        "description": "Search founders in Nigeria, Ghana and Kenya by sector, stage and evidence. See what our reviewers checked, then ask for an introduction.",
    },
    "trust": {
        "path": "/trust-and-safety",
        "title": "Trust and safety",
        "description": "IkonetU explains how it checks evidence, who sees what, what the IkonetU Score is and how to raise a concern.",
    },
    "readiness": {
        "path": "/readiness-check",
        "title": "Readiness self-check",
        "description": "Answer eleven questions, one for each area of the IkonetU Score, and see what to add first. You need no account, and nothing is saved.",
    },
    "privacy": {
        "path": "/privacy",
        "title": "Privacy policy",
        "description": "How IkonetU Technology Limited collects, uses and keeps personal data. Adopted on 15 October 2026.",
    },
    "terms": {
        "path": "/terms",
        "title": "Terms",
        "description": "The website terms, founder terms, investor terms, acceptable use policy and pitch licence of IkonetU. Adopted on 15 October 2026.",
    },
    "cookies": {
        "path": "/cookies",
        "title": "Cookie policy",
        "description": "The cookies and browser storage IkonetU uses, and how long each item lasts. Adopted on 15 October 2026.",
    },
}
