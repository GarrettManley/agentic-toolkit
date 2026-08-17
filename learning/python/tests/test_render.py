from sprint import render
from sprint.models import Ledger


def test_bar_endpoints_and_width():
    assert render.bar(0.0) == "-" * 10
    assert render.bar(1.0) == "#" * 10
    assert len(render.bar(0.37, width=20)) == 20


def test_bar_clamps_out_of_range():
    assert render.bar(-1.0) == "-" * 10
    assert render.bar(2.0) == "#" * 10


def test_status_screen_shows_level_xp_and_module_count():
    screen = render.status_screen(Ledger())
    assert "Novice" in screen
    assert "0 XP" in screen
    assert "0/2" in screen  # two built modules, none cleared


def test_skills_screen_handles_empty():
    assert "No skills tracked" in render.skills_screen(Ledger())
