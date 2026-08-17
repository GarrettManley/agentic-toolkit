from sprint import store
from sprint.models import Ledger, ModuleRecord, SkillMastery


def test_load_missing_file_returns_fresh_ledger(tmp_path):
    assert store.load(tmp_path / "ledger.json") == Ledger()


def test_save_then_load_round_trips_nested_records(tmp_path):
    original = Ledger(
        xp=220,
        combo=2,
        streak_days=3,
        last_active="2026-08-17",
        modules={
            "01": ModuleRecord("01", status="cleared", xp_awarded=220, peeked=False)
        },
        skills={"equality": SkillMastery("equality", 0.5)},
        achievements=["first-green"],
    )
    path = tmp_path / "ledger.json"

    store.save(path, original)
    reloaded = store.load(path)

    assert reloaded == original


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "ledger.json"
    store.save(path, Ledger(xp=10))
    assert path.exists()
    assert not (tmp_path / "ledger.tmp").exists()
