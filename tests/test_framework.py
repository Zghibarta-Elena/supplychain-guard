import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from supplyguard.cli import check_sbom, compare, inventory, main, simulate


class FrameworkTests(unittest.TestCase):
    def test_attack_patterns_detected(self):
        for scenario in ('solarwinds', 'xz'):
            self.assertTrue(simulate(scenario)['detected'])

    def test_changes_and_removal(self):
        self.assertEqual(compare({'a': '1', 'b': '2'}, {'a': '3', 'c': '4'}),
                         {'added': ['c'], 'removed': ['b'], 'changed': ['a']})

    def test_policy_and_nested_components(self):
        policy = json.loads(Path('policy.json').read_text())
        self.assertFalse(check_sbom(json.loads(Path('examples/clean.cdx.json').read_text()), policy))
        bad = json.loads(Path('examples/blocked.cdx.json').read_text())
        self.assertTrue(check_sbom(bad, policy))
        self.assertTrue(check_sbom({'bomFormat': 'CycloneDX', 'components': [
            {'name': 'parent', 'version': '1', 'purl': 'pkg:generic/parent@1', 'components': bad['components']}]}, policy))

    def test_empty_and_invalid_sbom(self):
        self.assertTrue(check_sbom({'bomFormat': 'CycloneDX', 'components': []}, {}))
        with self.assertRaises(ValueError):
            check_sbom({}, {})

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'link').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                inventory(directory)

    def test_cli_failure_codes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['check', 'examples/blocked.cdx.json']), 1)
            self.assertEqual(main(['check', 'examples/clean.cdx.json']), 0)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['check', 'missing.json']), 2)

    def test_verification_binds_identity_and_issuer(self):
        with patch('supplyguard.cli.run_tool') as runner:
            self.assertEqual(main(['verify', 'release.tar', '--bundle', 'bundle.json',
                                   '--identity', 'trusted@example.org', '--issuer', 'https://issuer.example']), 0)
            runner.assert_called_once_with(['cosign', 'verify-blob', 'release.tar', '--bundle', 'bundle.json',
                                           '--certificate-identity', 'trusted@example.org',
                                           '--certificate-oidc-issuer', 'https://issuer.example'])


if __name__ == '__main__':
    unittest.main()
