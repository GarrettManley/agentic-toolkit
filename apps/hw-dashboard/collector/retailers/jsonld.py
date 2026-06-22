"""Generic schema.org JSON-LD Product/Offer parser.

Most major retailers embed a <script type="application/ld+json"> Product block
with an `offers` object carrying price + availability. Parsing that structured
data is far more stable than scraping rendered HTML, so it's the default parser.
Returns None on any extraction failure (caller logs a warning)."""

from __future__ import annotations

import json
import re

from collector.models import PriceSnapshot, local_today, utc_now_iso

PARSER_VERSION = "jsonld@1"

_SCRIPT_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_IN_STOCK_RE = re.compile(
    r"InStock|LimitedAvailability|PreOrder|OnlineOnly", re.IGNORECASE
)


def _iter_objects(parsed):
    """Yield every dict in a parsed JSON-LD blob (handles @graph + lists)."""
    if isinstance(parsed, dict):
        if "@graph" in parsed and isinstance(parsed["@graph"], list):
            yield from _iter_objects(parsed["@graph"])
        yield parsed
    elif isinstance(parsed, list):
        for item in parsed:
            yield from _iter_objects(item)


def _first_offer(product: dict) -> dict | None:
    offers = product.get("offers")
    if isinstance(offers, dict):
        # AggregateOffer wraps individual offers; otherwise the dict IS the offer.
        if isinstance(offers.get("offers"), list) and offers["offers"]:
            return offers["offers"][0]
        return offers
    if isinstance(offers, list) and offers:
        return offers[0]
    return None


def parse(
    html: str, *, sku_id: str, retailer: str, url: str | None = None
) -> PriceSnapshot | None:
    for block in _SCRIPT_RE.findall(html):
        try:
            parsed = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for obj in _iter_objects(parsed):
            types = obj.get("@type", "")
            type_set = {types} if isinstance(types, str) else set(types or [])
            if "Product" not in type_set:
                continue
            offer = _first_offer(obj)
            if not offer:
                continue
            raw_price = offer.get("price") or offer.get("lowPrice")
            if raw_price is None:
                continue
            try:
                price = float(str(raw_price).replace(",", "").replace("$", ""))
            except ValueError:
                continue
            availability = str(offer.get("availability", ""))
            return PriceSnapshot(
                sku_id=sku_id,
                captured_at=utc_now_iso(),
                capture_date=local_today(),
                price=price,
                currency=offer.get("priceCurrency", "USD"),
                retailer=retailer,
                source="nightly-http",
                url=url,
                in_stock=bool(_IN_STOCK_RE.search(availability))
                if availability
                else None,
                source_detail={"parser_version": PARSER_VERSION},
            )
    return None
