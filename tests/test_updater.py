import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

SCRIPT = os.environ.get("UPDATER_SCRIPT", str(Path(__file__).resolve().parents[1] / "scripts/update-kernel.py"))
SPEC = importlib.util.spec_from_file_location("updater", SCRIPT)
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)

HASH = "sha256-" + base64.b64encode(bytes(32)).decode()
CURRENT = {
    "version": "7.2.11", "release": "cachyos-7.2.11-1", "sourceHash": HASH,
    "configRev": "a" * 40, "configHash": updater.sri(b"config"),
}
PKGBUILD = "_major=7.2\n_minor=11\n_tagrel=1\n#_rcver=rc8\n_srcname=cachyos-${_major}.${_minor}-${_tagrel}\n"
FINGERPRINT = updater.SIGNERS["ptr1337.asc"]
VALID = f"[GNUPG:] VALIDSIG {FINGERPRINT} 2026-10-15 1792064998 0 4 0 1 10 00 {FINGERPRINT}\n"


class SourcePolicyTests(unittest.TestCase):
    def test_literal_metadata(self):
        self.assertEqual(updater.parse_pkgbuild(PKGBUILD), ("7.2.11", "cachyos-7.2.11-1"))

    def test_never_evaluates_shell(self):
        for text in [PKGBUILD.replace("_minor=11", "_minor=$(touch /tmp/should-not-exist)"),
                     PKGBUILD + "_minor=12\n", PKGBUILD + "_rcver=rc8\n"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                updater.parse_pkgbuild(text)

    def test_rejects_nonstable_and_path_injection(self):
        for tag in ["cachyos-7.3-rc1-1", "cachyos-7.2.11-1/../../other", "7.2.11"]:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                updater.source_url(tag)

    def test_rejects_changed_source_naming(self):
        with self.assertRaisesRegex(ValueError, "source naming"):
            updater.parse_pkgbuild(PKGBUILD.replace("${_tagrel}", "${_tagrel}-custom"))

    def test_manifest_rejects_unpinned_or_malformed_inputs(self):
        for changes in [{"configRev": "master"}, {"configRev": "a" * 40 + "/config"},
                        {"version": "7.2.12"}, {"sourceHash": "sha256-YQ=="},
                        {"url": "https://evil.example/archive"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                updater.validate_manifest(CURRENT | changes)

    def test_redirect_strips_credentials(self):
        request = urllib.request.Request("https://api.github.com/example", headers={"Authorization": "Bearer private"})
        redirected = updater.SafeRedirects().redirect_request(
            request, None, 302, "Found", {}, "https://github.com/example")
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_rejects_unapproved_urls_and_redirects(self):
        for url in ["http://github.com/file", "https://github.com.evil.example/file",
                    "https://user@github.com/file", "https://github.com:8443/file"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                updater.validate_url(url)
        with self.assertRaises(ValueError):
            updater.SafeRedirects().redirect_request(
                urllib.request.Request("https://github.com/file"), None, 302, "Found", {}, "https://evil.example/file")

    def test_accepts_only_valid_approved_signer(self):
        updater.verify_signature_status(0, VALID)
        for code, status in [(1, VALID), (0, ""), (0, VALID.replace(FINGERPRINT, "F" * 40)),
                             (0, VALID + "[GNUPG:] EXPKEYSIG expired\n"),
                             (0, VALID + "[GNUPG:] BADSIG bad\n")]:
            with self.subTest(code=code, status=status), self.assertRaises(ValueError):
                updater.verify_signature_status(code, status)

    def latest(self, pkgbuild=PKGBUILD, digest="sha256:" + "00" * 32):
        tag = "cachyos-7.2.11-1"
        url = updater.source_url(tag)
        metadata = {"tag_name": tag, "draft": False, "prerelease": False, "assets": [
            {"name": tag + ".tar.gz", "browser_download_url": url, "digest": digest},
            {"name": tag + ".tar.gz.asc", "browser_download_url": url + ".asc"},
        ]}
        with patch.object(updater, "github_json", side_effect=[{"sha": "b" * 40}, metadata]), \
             patch.object(updater, "download", side_effect=[pkgbuild.encode(), b"config"]):
            return updater.latest_sources(CURRENT)

    def test_unchanged_config_retains_existing_pin(self):
        self.assertEqual(self.latest(), CURRENT)

    def test_rejects_replaced_release(self):
        with self.assertRaisesRegex(ValueError, "existing release"):
            self.latest(digest="sha256:" + "11" * 32)

    def test_requires_release_digest(self):
        with self.assertRaisesRegex(ValueError, "digest"):
            self.latest(digest=None)

    def test_rejects_downgrade(self):
        with self.assertRaisesRegex(ValueError, "downgrade"):
            self.latest(pkgbuild=PKGBUILD.replace("_minor=11", "_minor=10"))

    def test_failed_verification_never_changes_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "sources.json"
            original = json.dumps(CURRENT)
            manifest.write_text(original)
            candidate = CURRENT | {"release": "cachyos-7.2.12-1", "version": "7.2.12"}
            with patch.object(updater, "MANIFEST", manifest), \
                 patch.object(updater, "latest_sources", return_value=candidate), \
                 patch.object(updater, "verify_sources", side_effect=ValueError("bad signature")), \
                 patch("sys.argv", ["update-kernel.py"]), self.assertRaises(ValueError):
                updater.main()
            self.assertEqual(manifest.read_text(), original)


if __name__ == "__main__":
    unittest.main()
