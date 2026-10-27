import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("copilot_build", ROOT / "copilot" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def files():
    result = {str(p.relative_to(build.PACKAGE)): p.read_bytes() for p in build.PACKAGE.rglob("*") if p.is_file()}
    manifest = json.loads(result["manifest.json"])
    manifest["agentConnectors"][0]["toolSource"]["remoteMcpServer"]["authorization"]["referenceId"] = build.PLACEHOLDER
    result["manifest.json"] = json.dumps(manifest).encode()
    return result


def test_draft_passes_schema_and_package_checks():
    build.validate_contents(files(), draft=True)


def test_release_rejects_placeholder_auth():
    with pytest.raises(AssertionError, match="Missing real OAuth"):
        build.validate_contents(files())


def test_release_requires_registration_environment(monkeypatch):
    monkeypatch.delenv("RESEMBLE_OAUTH_REFERENCE_ID", raising=False)
    with pytest.raises(SystemExit, match="Release build blocked"):
        build.build()


def test_release_accepts_padded_microsoft_vault_id(monkeypatch, tmp_path):
    monkeypatch.setenv("RESEMBLE_OAUTH_REFERENCE_ID", "dGVuYW50IyNjb25maWd1cmF0aW9uLWlk=")
    monkeypatch.setattr(build, "ROOT", tmp_path)
    package = build.build()
    assert package.exists()


def test_microsoft_requires_nonzero_major_version():
    content = files()
    manifest = json.loads(content["manifest.json"])
    manifest["version"] = "0.1.0"
    content["manifest.json"] = json.dumps(manifest).encode()
    with pytest.raises(AssertionError, match="major version"):
        build.validate_contents(content, draft=True)


def test_skill_mismatch_is_rejected():
    content = files()
    path = "skills/media-authenticity/SKILL.md"
    content[path] = content[path].replace(b"name: media-authenticity", b"name: wrong-name")
    with pytest.raises(AssertionError):
        build.validate_contents(content, draft=True)


def test_source_pack_does_not_contain_credentials():
    for path, content in files().items():
        if path.endswith((".md", ".json")):
            assert b"Bearer eyJ" not in content
            assert b"client_secret\":\"" not in content
            assert b"oauth_at_" not in content
