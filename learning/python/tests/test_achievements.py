from sprint import achievements
from sprint.models import Ledger, ModuleRecord


def _ids(badges):
    return {badge.id for badge in badges}


def test_first_green_unlocks_after_one_pass():
    ledger = Ledger(modules={"00": ModuleRecord("00", status="passed")})
    assert "first-green" in _ids(achievements.newly_unlocked(ledger))


def test_no_peek_novice_requires_a_no_peek_clear():
    peeked = Ledger(modules={"00": ModuleRecord("00", status="passed", peeked=True)})
    assert "no-peek-novice" not in _ids(achievements.newly_unlocked(peeked))

    clean = Ledger(modules={"00": ModuleRecord("00", status="passed", peeked=False)})
    assert "no-peek-novice" in _ids(achievements.newly_unlocked(clean))


def test_centurion_unlocks_at_1000_xp():
    assert "centurion" not in _ids(achievements.newly_unlocked(Ledger(xp=999)))
    assert "centurion" in _ids(achievements.newly_unlocked(Ledger(xp=1000)))


def test_newly_unlocked_excludes_already_owned():
    ledger = Ledger(
        xp=1000,
        modules={"00": ModuleRecord("00", status="passed", peeked=False)},
        achievements=["first-green", "centurion", "no-peek-novice"],
    )
    fresh = _ids(achievements.newly_unlocked(ledger))
    assert "first-green" not in fresh
    assert "centurion" not in fresh
