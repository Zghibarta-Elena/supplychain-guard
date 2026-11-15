import copy
import unittest

from supplyguard import experiments


class ExperimentMetricsTests(unittest.TestCase):
    def test_cli_dispatches_preparation_explicitly(self):
        from unittest.mock import patch
        from supplyguard.cli import main
        with patch('supplyguard.experiments.main') as runner:
            self.assertEqual(main(['experiment', '--prepare']), 0)
            runner.assert_called_once_with(['--prepare'])

    def test_reference_deduplicates_installed_paths(self):
        lock = {'packages': {'': {'name': 'root', 'version': '1'},
                             'node_modules/a': {'version': '1'},
                             'node_modules/dev/node_modules/a': {'version': '1', 'dev': True},
                             'node_modules/dev': {'version': '2', 'dev': True}}}
        all_ref, prod = experiments.npm_reference(lock)
        self.assertEqual(all_ref, {('a', '1'), ('dev', '2')})
        self.assertEqual(prod, {('a', '1')})

    def test_hash_completion_preserves_existing_and_scoped_names(self):
        import base64
        sri = 'sha512-' + base64.b64encode(bytes(range(64))).decode()
        doc = {'components': [{'name': 'a', 'group': '@scope', 'version': '1',
                               'purl': 'pkg:npm/%40scope/a@1'}]}
        lock = {'packages': {'node_modules/@scope/a': {'version': '1', 'integrity': sri}}}
        self.assertEqual(experiments.add_hashes(doc, lock), 1)
        self.assertEqual(doc['components'][0]['hashes'], [{'alg': 'SHA-512', 'content': bytes(range(64)).hex()}])
        existing = copy.deepcopy(doc)
        self.assertEqual(experiments.add_hashes(doc, lock), 0)
        self.assertEqual(doc, existing)

    def test_conflicting_integrity_not_guessed(self):
        doc = {'components': [{'name': 'a', 'version': '1', 'purl': 'pkg:npm/a@1'}]}
        lock = {'packages': {'node_modules/a': {'version': '1', 'integrity': 'sha512-one'},
                             'node_modules/b/node_modules/a': {'version': '1', 'integrity': 'sha512-two'}}}
        self.assertEqual(experiments.add_hashes(doc, lock), 0)
        self.assertNotIn('hashes', doc['components'][0])
