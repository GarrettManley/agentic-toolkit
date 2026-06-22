from pathlib import Path
import pytest


def test_win_to_wsl_c_drive():
    from sandbox._wslpath import win_to_wsl
    assert win_to_wsl(r"C:\Users\Garre\Workspace\sec-research") == "/mnt/c/Users/Garre/Workspace/sec-research"


def test_win_to_wsl_lowercases_drive():
    from sandbox._wslpath import win_to_wsl
    assert win_to_wsl(r"D:\data\x") == "/mnt/d/data/x"


def test_win_to_wsl_accepts_path_object():
    from sandbox._wslpath import win_to_wsl
    out = win_to_wsl(Path("C:/Users/Garre/x"))
    assert out == "/mnt/c/Users/Garre/x"
