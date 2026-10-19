#!/usr/bin/env python3
"""Update pinned CachyOS server sources without executing upstream build scripts."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "kernel/sources.json"
API = "https://api.github.com/repos/CachyOS"
SIGNERS = {
    "ptr1337.asc": "E8B9AA39F054E30E8290D492C3C4820857F654FE",
    "naim.asc": "E18447AC260021D31F3FF6C4C8A2A4774B8B63C4",
}
HOSTS = {
    "api.github.com", "github.com", "raw.githubusercontent.com",
    "release-assets.githubusercontent.com", "objects.githubusercontent.com",
}
RELEASE = re.compile(r"cachyos-(\d+)\.(\d+)\.(\d+)-(\d+)")


def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in HOSTS
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError(f"Unapproved download URL: {url}")


class SafeRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


def download(url, destination=None):
    validate_url(url)
    headers = {"User-Agent": "linux-ms-7e79-source-updater"}
    token = os.environ.get("GITHUB_TOKEN")
    if urllib.parse.urlsplit(url).hostname == "api.github.com" and token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(SafeRedirects())
    # Bound both metadata and source archive sizes. Never load the archive into RAM.
    limit = 1024 * 1024 * 1024 if destination else 2 * 1024 * 1024
    with opener.open(request, timeout=60) as response:
        validate_url(response.url)
        if destination:
            with destination.open("wb") as output:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > limit:
                        raise ValueError("Source archive exceeds size limit")
                    output.write(chunk)
            return None
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Metadata exceeds size limit")
        return data


def github_json(path):
    return json.loads(download(f"{API}/{path}"))


def sri(data):
    return "sha256-" + base64.b64encode(hashlib.sha256(data).digest()).decode()


def release_number(tag):
    match = RELEASE.fullmatch(tag)
    if not match:
        raise ValueError(f"Not a stable CachyOS release: {tag}")
    return tuple(map(int, match.groups()))


def parse_pkgbuild(text):
    # Read only literal numeric assignments. Never source or execute PKGBUILD.
    if re.search(r"^_rcver=", text, re.MULTILINE):
        raise ValueError("Release candidate packaging is not supported")
    names = re.findall(r"^_srcname=(.*?)\s*$", text, re.MULTILINE)
    if names != ["cachyos-${_major}.${_minor}-${_tagrel}"]:
        raise ValueError("Upstream source naming changed; review the metadata parser")
    def literal(name, pattern):
        values = re.findall(rf"^{name}=({pattern})\s*(?:#.*)?$", text, re.MULTILINE)
        if len(values) != 1:
            raise ValueError(f"Expected one literal {name} assignment")
        return values[0]

    major = literal("_major", r"[0-9]+\.[0-9]+")
    minor = literal("_minor", r"[0-9]+")
    revision = literal("_tagrel", r"[0-9]+")
    version = f"{major}.{minor}"
    return version, f"cachyos-{version}-{revision}"


def source_url(release):
    release_number(release)
    return f"https://github.com/CachyOS/linux/releases/download/{release}/{release}.tar.gz"


def validate_manifest(manifest):
    if set(manifest) != {"version", "release", "sourceHash", "configRev", "configHash"}:
        raise ValueError("Unexpected source manifest fields")
    version = ".".join(map(str, release_number(manifest["release"])[:3]))
    if manifest["version"] != version:
        raise ValueError("Source version does not match release tag")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest["configRev"]):
        raise ValueError("Configuration must be pinned to a full Git commit")
    for key in ("sourceHash", "configHash"):
        if not manifest[key].startswith("sha256-"):
            raise ValueError(f"Invalid {key}")
        if len(base64.b64decode(manifest[key][7:], validate=True)) != 32:
            raise ValueError(f"Invalid {key}")


def latest_sources(current):
    # Use one immutable tree for PKGBUILD and config, avoiding branch-update races.
    commit = github_json("linux-cachyos/commits/master")["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid upstream commit")
    base = f"https://raw.githubusercontent.com/CachyOS/linux-cachyos/{commit}/linux-cachyos-server"
    version, tag = parse_pkgbuild(download(f"{base}/PKGBUILD").decode())
    if release_number(tag) < release_number(current["release"]):
        raise ValueError("Refusing a source version downgrade")
    release = github_json(f"linux/releases/tags/{tag}")
    if release.get("draft") or release.get("prerelease") or release["tag_name"] != tag:
        raise ValueError("Expected a published stable release")
    name = f"{tag}.tar.gz"
    assets = {asset["name"]: asset for asset in release["assets"]}
    asset = assets[name]
    if asset["browser_download_url"] != source_url(tag):
        raise ValueError("Unexpected source asset URL")
    if assets[name + ".asc"]["browser_download_url"] != source_url(tag) + ".asc":
        raise ValueError("Unexpected signature asset URL")
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("GitHub release is missing its SHA-256 asset digest")
    config_hash = sri(download(f"{base}/config"))
    candidate = {
        "version": version,
        "release": tag,
        "sourceHash": "sha256-" + base64.b64encode(bytes.fromhex(digest[7:])).decode(),
        # A new packaging commit with identical config does not require a rebuild.
        "configRev": current["configRev"] if config_hash == current["configHash"] else commit,
        "configHash": config_hash,
    }
    validate_manifest(candidate)
    if tag == current["release"] and candidate["sourceHash"] != current["sourceHash"]:
        raise ValueError("An existing release archive changed; manual investigation required")
    return candidate


def verify_sources(manifest):
    validate_manifest(manifest)
    config_url = ("https://raw.githubusercontent.com/CachyOS/linux-cachyos/"
                  f"{manifest['configRev']}/linux-cachyos-server/config")
    if sri(download(config_url)) != manifest["configHash"]:
        raise ValueError("Configuration hash mismatch")
    with tempfile.TemporaryDirectory(prefix="cachyos-verify-") as directory:
        work = Path(directory)
        archive = work / "source.tar.gz"
        signature = work / "source.tar.gz.asc"
        print(f"Verifying official source: {manifest['release']}", flush=True)
        download(source_url(manifest["release"]), archive)
        with archive.open("rb") as source:
            actual = "sha256-" + base64.b64encode(hashlib.file_digest(source, "sha256").digest()).decode()
        if actual != manifest["sourceHash"]:
            raise ValueError("Source archive hash mismatch")
        download(source_url(manifest["release"]) + ".asc", signature)
        home = work / "gnupg"
        home.mkdir(mode=0o700)
        command = ["gpg", "--no-options", "--batch", "--homedir", str(home),
                   "--no-auto-key-retrieve", "--auto-key-locate", "clear"]
        for filename, fingerprint in SIGNERS.items():
            key = ROOT / "kernel/keys" / filename
            listing = subprocess.run(
                command + ["--with-colons", "--show-keys", str(key)],
                check=True, capture_output=True, text=True,
            ).stdout
            primary = listing.split("fpr:", 1)[1].splitlines()[0].split(":")[8]
            if primary != fingerprint or listing.count("pub:") != 1:
                raise ValueError(f"Unexpected signing key in {filename}")
            subprocess.run(command + ["--import", str(key)], check=True, capture_output=True)
        result = subprocess.run(
            command + ["--status-fd", "1", "--verify", str(signature), str(archive)],
            capture_output=True, text=True,
        )
        verify_signature_status(result.returncode, result.stdout)
        print("Official source signature and hashes verified.", flush=True)


def verify_signature_status(returncode, status):
    bad = ("BADSIG", "ERRSIG", "REVKEYSIG", "EXPKEYSIG", "EXPSIG",
           "KEYEXPIRED", "SIGEXPIRED", "KEYREVOKED")
    if returncode or any(f"[GNUPG:] {flag} " in status for flag in bad):
        raise ValueError("Source signature verification failed")
    valid = [line.split() for line in status.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")]
    if (len(valid) != 1 or len(valid[0]) < 12
            or not ({valid[0][2], valid[0][-1]} & set(SIGNERS.values()))):
        raise ValueError("Source was not signed by an approved CachyOS signer")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Verify current pins without updating")
    parser.add_argument("--check", action="store_true", help="Check for updates without writing files")
    args = parser.parse_args()
    current = json.loads(MANIFEST.read_text())
    validate_manifest(current)
    if args.verify:
        verify_sources(current)
        return
    candidate = latest_sources(current)
    if candidate == current:
        print(f"Already up to date: {current['release']}")
        return
    verify_sources(candidate)
    if not args.check:
        temporary = MANIFEST.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(candidate, indent=2) + "\n")
        temporary.replace(MANIFEST)
    print(json.dumps(candidate, indent=2))


if __name__ == "__main__":
    main()
