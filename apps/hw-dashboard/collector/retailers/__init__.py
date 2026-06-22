"""Retailer parsers: each exposes `parse(html, *, sku_id, retailer, url) ->
PriceSnapshot | None` and a `PARSER_VERSION`. A parser returns None (not raises)
when it can't extract a price, so a layout change degrades to a warning rather
than crashing the nightly run."""
