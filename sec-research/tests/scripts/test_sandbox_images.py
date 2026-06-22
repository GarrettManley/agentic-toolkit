import pytest


def test_image_for_known_ecosystems():
    from sandbox._images import image_for
    assert image_for("npm") == "node:22-slim"
    assert image_for("pypi") == "python:3.12-slim"
    assert image_for("cargo") == "rust:1-slim"
    assert image_for("rubygems") == "ruby:3.3-slim"


def test_image_for_unknown_raises():
    from sandbox._images import image_for, UnknownEcosystem
    with pytest.raises(UnknownEcosystem):
        image_for("maven")


def test_registry_for_and_hosts():
    from sandbox._images import registry_for, REGISTRY_HOSTS
    assert registry_for("npm") == "registry.npmjs.org"
    assert "pypi.org" in REGISTRY_HOSTS and "crates.io" in REGISTRY_HOSTS


def test_safe_install_env_npm_disables_scripts():
    from sandbox._images import safe_install_env
    env = safe_install_env("npm")
    # env is a flat list of docker -e flag pairs
    assert "-e" in env and any("ignore_scripts=true" in e for e in env)


def test_safe_install_env_unknown_is_empty():
    from sandbox._images import safe_install_env
    assert safe_install_env("cargo") == []  # cargo has no global script-disable in v1
