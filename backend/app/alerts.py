"""Manual H-1B news cards. No X ingest. USCIS.gov sources only."""

from __future__ import annotations

from typing import Any

ALERT_TAGS = ("policy_alert", "news_release", "fee_change")

SEED_ALERTS = (
    {
        "alertId": "h1b-cap-season",
        "title": "H-1B Cap Season",
        "sourceUrl": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations/h-1b-cap-season",
        "publishedOn": "2026-09-10",
        "tag": "policy_alert",
        "summary": (
            "USCIS explains the H-1B program and the annual regular cap (65,000) plus the "
            "20,000 exemption for certain U.S. master's and higher degrees. Some petitioners "
            "are cap-exempt. Verify the current page on USCIS.gov."
        ),
    },
    {
        "alertId": "h1b-specialty-occupations",
        "title": "H-1B Specialty Occupations",
        "sourceUrl": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        "publishedOn": "2026-09-10",
        "tag": "policy_alert",
        "summary": (
            "Cap-subject H-1B filings use an electronic registration process when that "
            "requirement is in effect. Petitioners generally include a DOL-certified Labor "
            "Condition Application with Form I-129. Verify on USCIS.gov."
        ),
    },
    {
        "alertId": "uscis-newsroom",
        "title": "USCIS Newsroom",
        "sourceUrl": "https://www.uscis.gov/newsroom/news-releases",
        "publishedOn": "2026-09-10",
        "tag": "news_release",
        "summary": (
            "Official USCIS news releases. TurboImmi lists this page instead of scraping "
            "social media. Always open the linked USCIS.gov article."
        ),
    },
)


def alert_pk() -> str:
    return "ALERT"


def alert_sk(published_on: str, alert_id: str) -> str:
    return f"DATE#{published_on}#{alert_id}"


def seed_alert_items() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in SEED_ALERTS:
        item = dict(raw)
        if item["tag"] not in ALERT_TAGS:
            raise ValueError(f"unknown alert tag {item['tag']}")
        if "uscis.gov" not in str(item["sourceUrl"]):
            raise ValueError("alert sourceUrl must be USCIS.gov")
        item["pk"] = alert_pk()
        item["sk"] = alert_sk(str(item["publishedOn"]), str(item["alertId"]))
        rows.append(item)
    return rows


def public_alert(item: dict[str, Any]) -> dict[str, str]:
    return {
        "alertId": str(item.get("alertId") or ""),
        "title": str(item.get("title") or ""),
        "sourceUrl": str(item.get("sourceUrl") or ""),
        "publishedOn": str(item.get("publishedOn") or ""),
        "tag": str(item.get("tag") or ""),
        "summary": str(item.get("summary") or ""),
    }
