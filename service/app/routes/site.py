"""The eleven public pages of the website."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..pages import PUBLIC_PAGES
from ..web import Meta, render

router = APIRouter()

# The template of each page, named after the page class its board gives it (pg-home and so on).
TEMPLATES = {
    "home": "home", "founders": "founders", "investors": "investors", "how": "how", "trust": "trust",
    "about": "about", "questions": "questions", "readiness": "readiness", "privacy": "privacy",
    "terms": "terms", "cookies": "cookies",
}


def _page(key: str):
    page = PUBLIC_PAGES[key]

    async def show(request: Request):
        meta = Meta(
            title=page["title"], description=page["description"], canonical=page["path"],
            absolute_title=key == "home",
        )
        return render(request, "site/page.html", {"page_template": f"site/pages/{TEMPLATES[key]}.html"}, meta)

    show.__name__ = f"page_{key}"
    return show


for _key, _page_info in PUBLIC_PAGES.items():
    router.add_api_route(_page_info["path"], _page(_key), methods=["GET"], include_in_schema=False)
