import tempfile
from pathlib import Path
import unittest
from supplyguard.gui import build_command, result_rows


class GuiCommandTests(unittest.TestCase):
    def test_experiments_command(self):
        self.assertEqual(build_command('Experimente capitolele 4 și 5', {})[-1], 'experiment')

    def test_simulation(self):
        self.assertEqual(build_command('Laborator atacuri', {'scenario': 'xz'})[-2:], ['simulate', 'xz'])

    def test_missing_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'app'
            artifact.write_text('demo')
            with self.assertRaisesRegex(ValueError, 'Identitate'):
                build_command('Verificare semnătură', {'artifact': str(artifact), '--bundle': str(artifact)})

    def test_spaces_and_shell_characters_remain_literal(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'app with spaces;echo'
            source.mkdir()
            output = str(Path(directory) / 'sbom.json')
            argv = build_command('Generare SBOM', {'source': str(source), '--output': output})
            self.assertEqual(argv[-3:], ['dir:' + str(source), '--output', output])

    def test_invalid_input_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Fișier inexistent'):
            build_command('Verificare SBOM', {'sbom': '/missing-supplyguard-file', '--policy': 'policy.json'})


class ResultTableTests(unittest.TestCase):
    def test_nested_findings(self):
        rows = result_rows('{"detected": true, "differences": {"changed": ["app.txt"], "added": []}}', 0)
        self.assertIn(('detected', 'Da'), rows)
        self.assertIn(('differences.changed[1]', 'app.txt'), rows)
        self.assertIn(('differences.added', '—'), rows)

    def test_tool_error_preserved(self):
        self.assertIn(('Mesaj', 'Error: missing tool'), result_rows('Error: missing tool', 2))
