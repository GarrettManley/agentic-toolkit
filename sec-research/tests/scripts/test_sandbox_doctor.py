import subprocess
import types


def _runner(script):
    """script: callable(argv) -> SimpleNamespace(returncode, stdout, stderr)."""
    def runner(argv, **kw):
        return script(argv)
    return runner


def test_doctor_ok_when_docker_and_images_present():
    from sandbox.doctor import sandbox_doctor
    def script(argv):
        if "info" in argv:
            return types.SimpleNamespace(returncode=0, stdout="Server Version: 27", stderr="")
        if "inspect" in argv:
            return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is True


def test_doctor_fails_when_docker_unreachable():
    from sandbox.doctor import sandbox_doctor
    def script(argv):
        if "info" in argv:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="Cannot connect")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is False and any("docker" in m.lower() for m in msgs)


def test_doctor_pulls_missing_image():
    from sandbox.doctor import sandbox_doctor
    pulled = []
    def script(argv):
        if "info" in argv:
            return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
        if "inspect" in argv:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="No such image")
        if "pull" in argv:
            pulled.append(argv[-1])
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is True and "node:22-slim" in pulled


def test_doctor_main_returns_one_when_unreachable(monkeypatch):
    import sandbox.doctor as d
    monkeypatch.setattr(d, "sandbox_doctor", lambda **kw: (False, ["docker unreachable"]))
    assert d.main([]) == 1


def test_doctor_fails_when_wsl_not_found():
    from sandbox.doctor import sandbox_doctor
    def script(argv):
        raise FileNotFoundError("wsl not found")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is False and msgs


def test_doctor_fails_when_pull_fails():
    import types
    from sandbox.doctor import sandbox_doctor
    def script(argv):
        if "info" in argv:
            return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
        if "inspect" in argv:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="No such image")
        if "pull" in argv:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="pull failed")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    ok, msgs = sandbox_doctor(runner=_runner(script))
    assert ok is False and any("pull" in m.lower() for m in msgs)
