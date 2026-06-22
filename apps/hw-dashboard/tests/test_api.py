"""API tests — FastAPI TestClient over an isolated tmp data tree. No network."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.server import WEBHOOK_TOKEN_ENV, app
from collector import paths

client = TestClient(app)


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_components_list_and_single(tmp_data):
    _write(
        paths.COMPONENTS_DIR / "rtx-4060-ti-16gb.json",
        {
            "component_id": "rtx-4060-ti-16gb",
            "category": "gpu",
            "name": "RTX 4060 Ti 16GB",
            "manufacturer": "NVIDIA",
            "created_at": "2026-06-22T00:00:00Z",
        },
    )
    assert len(client.get("/api/components").json()) == 1
    assert client.get("/api/components/rtx-4060-ti-16gb").json()["category"] == "gpu"
    assert client.get("/api/components/nope").status_code == 404


def test_series_merges_seed_and_first_party(tmp_data):
    paths.seed_path("s1").write_text(
        json.dumps(
            {
                "sku_id": "s1",
                "capture_date": "2026-01-01",
                "price": 500,
                "currency": "USD",
                "source": "seed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    paths.series_path("s1").write_text(
        json.dumps(
            {
                "sku_id": "s1",
                "capture_date": "2026-06-22",
                "price": 450,
                "currency": "USD",
                "retailer": "newegg",
                "source": "nightly-http",
                "captured_at": "2026-06-22T09:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rows = client.get("/api/skus/s1/series").json()
    assert [r["capture_date"] for r in rows] == ["2026-01-01", "2026-06-22"]


def test_recompute_then_get_analytics(tmp_data):
    _write(
        paths.SKUS_DIR / "s1.json",
        {
            "sku_id": "s1",
            "component_id": "c1",
            "display_name": "S1",
            "tracked_urls": [{"retailer": "newegg", "url": "https://x/p"}],
            "currency": "USD",
            "active": True,
            "created_at": "2026-06-22T00:00:00Z",
        },
    )
    paths.series_path("s1").write_text(
        "\n".join(
            json.dumps(
                {
                    "sku_id": "s1",
                    "capture_date": f"2026-09-{d:02d}",
                    "price": 450 - d,
                    "currency": "USD",
                    "retailer": "newegg",
                    "source": "nightly-http",
                }
            )
            for d in range(1, 6)
        )
        + "\n",
        encoding="utf-8",
    )

    resp = client.post("/api/analytics/recompute", json={"sku_id": "s1"})
    assert resp.status_code == 200
    assert resp.json()["history_days"] == 5
    assert client.get("/api/analytics/s1").json()["sku_id"] == "s1"


def test_webhook_rejects_bad_token(tmp_data, monkeypatch):
    monkeypatch.setenv(WEBHOOK_TOKEN_ENV, "secret123")
    assert (
        client.post(
            "/api/webhook/firecrawl?token=wrong", json={"sku_id": "s1"}
        ).status_code
        == 401
    )
    ok = client.post(
        "/api/webhook/firecrawl?token=secret123",
        json={"sku_id": "s1", "price": 419.99, "retailer": "newegg"},
    )
    assert ok.status_code == 200
    assert list(paths.INTAKE_DIR.glob("*.json"))  # payload spooled
