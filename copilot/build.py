"""Build a reproducible M365 package. Release builds require a real vault reference.

Run from the repository root: .venv/bin/python copilot/build.py [--draft]
Only the public Microsoft OAuth registration reference goes into the archive.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

import jsonschema
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "appPackage"
SCHEMA = ROOT / "schema" / "MicrosoftTeams-v1.29.schema.json"
PLACEHOLDER = "UNCONFIGURED_OAUTH_REFERENCE"


def validate_contents(files, *, draft=False):
    manifest = json.loads(files["manifest.json"])
    jsonschema.Draft7Validator(json.loads(SCHEMA.read_text())).validate(manifest)
    assert int(manifest["version"].split(".")[0]) >= 1, "Microsoft requires an app major version of at least 1"
    connector = manifest["agentConnectors"][0]["toolSource"]["remoteMcpServer"]
    auth = connector["authorization"]
    assert auth["type"] == "OAuthPluginVault", "Cowork requires OAuth for this connector"
    assert connector["mcpServerUrl"].startswith("https://"), "HTTPS required"
    assert not re.search(r"\$\{|placeholder|unconfigured|example", auth["referenceId"], re.I) or draft, "Missing real OAuth vault registration"
    assert len(files) == len(set(files)), "Duplicate paths"
    for path in files:
        assert not path.startswith("/") and ".." not in Path(path).parts and "\\" not in path
        assert not any(p.startswith(".") for p in Path(path).parts)
    folders = [s["folder"].removeprefix("./") for s in manifest["agentSkills"]]
    assert len(folders) == len(set(folders)) <= 20
    for folder in folders:
        skill = files[f"{folder}/SKILL.md"].decode()
        assert skill.startswith("---\n")
        metadata = yaml.safe_load(skill.split("---", 2)[1])
        assert metadata["name"] == Path(folder).name
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", metadata["name"])
        assert 1 <= len(metadata["name"]) <= 64
        assert 1 <= len(metadata["description"]) <= 1024
        companions = {p: b for p, b in files.items() if p.startswith(folder + "/") and p != folder + "/SKILL.md"}
        assert len(companions) <= 20
        assert all(len(b) <= 5 * 1024 * 1024 for b in companions.values())
        assert sum(map(len, companions.values())) <= 10 * 1024 * 1024
    from io import BytesIO
    for name, size in [("color.png", (192, 192)), ("outline.png", (32, 32))]:
        with Image.open(BytesIO(files[name])) as image:
            assert image.format == "PNG" and image.size == size
    return manifest


def build(draft=False):
    reference = os.getenv("RESEMBLE_OAUTH_REFERENCE_ID", "")
    # Microsoft's current opaque vault IDs are padded base64, not UUIDs.
    if not draft and (not reference or not re.fullmatch(r"[A-Za-z0-9_+/-]{8,512}={0,2}", reference)):
        raise SystemExit("Release build blocked: set RESEMBLE_OAUTH_REFERENCE_ID to the actual Microsoft token-vault registration ID. Use --draft only for offline validation.")
    files = {str(p.relative_to(PACKAGE)): p.read_bytes() for p in sorted(PACKAGE.rglob("*")) if p.is_file()}
    manifest = json.loads(files["manifest.json"])
    manifest["agentConnectors"][0]["toolSource"]["remoteMcpServer"]["authorization"]["referenceId"] = PLACEHOLDER if draft else reference
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    validate_contents(files, draft=draft)
    out = ROOT / "dist" / ("resemble-cowork-DRAFT.zip" if draft else f"resemble-cowork-{manifest['version']}.zip")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(2026, 10, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(out) as archive:
        assert archive.testzip() is None
        validate_contents({n: archive.read(n) for n in archive.namelist()}, draft=draft)
    print(json.dumps({"package": str(out), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                      "files": len(files), "draft": draft, "cowork_e2e_verified": False}, indent=2))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true", help="Offline review package only; cannot connect until OAuth is configured.")
    build(parser.parse_args().draft)
