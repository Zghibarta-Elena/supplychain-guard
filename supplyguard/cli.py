"""Offline policy checks and explicit integrations with Syft and Sigstore Cosign."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Inventory root must be a directory')
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlinks are not allowed: {path}')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def compare(expected, actual):
    return {
        'added': sorted(actual.keys() - expected.keys()),
        'removed': sorted(expected.keys() - actual.keys()),
        'changed': sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k]),
    }


def check_sbom(sbom, policy):
    if sbom.get('bomFormat') != 'CycloneDX' or not isinstance(sbom.get('components'), list):
        raise ValueError('Expected a CycloneDX JSON SBOM with a components array')
    findings = []
    components = sbom['components']
    if not components:
        findings.append('SBOM contains no components')
    def visit(component):
        name, version = component.get('name'), component.get('version')
        if not name or not version:
            findings.append(f'Missing name/version: {name or "<unnamed>"}')
        if policy.get('require_purl', True) and not component.get('purl'):
            findings.append(f'Missing package URL: {name}')
        for rule in policy.get('deny', []):
            if name == rule['name'] and version in rule['versions']:
                findings.append(f'Denied component: {name}@{version}: {rule["reason"]}')
        for child in component.get('components', []):
            visit(child)
    for component in components:
        visit(component)
    return findings


def run_tool(args):
    subprocess.run(args, check=True)


def simulate(scenario):
    with tempfile.TemporaryDirectory(prefix='supplyguard-') as directory:
        root = Path(directory)
        (root / 'application.txt').write_text('approved application\n')
        baseline = inventory(root)
        if scenario == 'solarwinds':
            (root / 'application.txt').write_text('approved application\nSIMULATED BUILD INJECTION\n')
        else:
            (root / 'release-only.m4').write_text('SIMULATED TARBALL-ONLY BUILD INPUT\n')
        differences = compare(baseline, inventory(root))
        return {'scenario': scenario, 'simulation': True, 'detected': any(differences.values()),
                'differences': differences,
                'limitation': 'A trusted baseline is required; this is a harmless illustration, not an exploit or historical reproduction.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('snapshot', help='Create a SHA-256 inventory; store it outside the scanned directory')
    p.add_argument('directory'); p.add_argument('--output', required=True)
    p = commands.add_parser('compare', help='Compare a directory against a trusted inventory')
    p.add_argument('directory'); p.add_argument('--baseline', required=True)
    p = commands.add_parser('sbom', help='Generate a CycloneDX SBOM using installed Syft')
    p.add_argument('source'); p.add_argument('--output', required=True)
    p = commands.add_parser('check', help='Evaluate CycloneDX components against local policy')
    p.add_argument('sbom'); p.add_argument('--policy', default='policy.json')
    for command in ('sign', 'verify'):
        p = commands.add_parser(command, help=f'{command.title()} an artifact using installed Cosign')
        p.add_argument('artifact'); p.add_argument('--bundle', required=True)
        if command == 'verify':
            p.add_argument('--identity', required=True); p.add_argument('--issuer', required=True)
    p = commands.add_parser('simulate', help='Run a harmless attack-pattern illustration')
    p.add_argument('scenario', choices=['solarwinds', 'xz'])
    p = commands.add_parser('experiment', help='Run real Express/Flask SBOM and Cosign E1/E2 experiments (Python 3.11+)')
    p.add_argument('--prepare', action='store_true', help='Download source projects and checksum-verified Syft binaries')
    args = parser.parse_args(argv)
    try:
        if args.command == 'snapshot':
            root, output = Path(args.directory).resolve(), Path(args.output).resolve()
            if output == root or root in output.parents:
                raise ValueError('Snapshot output must be outside the scanned directory')
            output.write_text(json.dumps(inventory(root), indent=2) + '\n')
        elif args.command == 'compare':
            differences = compare(json.loads(Path(args.baseline).read_text()), inventory(args.directory))
            print(json.dumps(differences, indent=2))
            return int(any(differences.values()))
        elif args.command == 'sbom':
            run_tool(['syft', args.source, '-o', f'cyclonedx-json={args.output}'])
        elif args.command == 'check':
            findings = check_sbom(json.loads(Path(args.sbom).read_text()), json.loads(Path(args.policy).read_text()))
            print(json.dumps({'passed': not findings, 'findings': findings}, indent=2))
            return int(bool(findings))
        elif args.command == 'sign':
            run_tool(['cosign', 'sign-blob', args.artifact, '--bundle', args.bundle, '--yes'])
        elif args.command == 'verify':
            run_tool(['cosign', 'verify-blob', args.artifact, '--bundle', args.bundle,
                      '--certificate-identity', args.identity, '--certificate-oidc-issuer', args.issuer])
        elif args.command == 'experiment':
            from .experiments import main as experiment_main
            experiment_main(['--prepare'] if args.prepare else [])
        else:
            print(json.dumps(simulate(args.scenario), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2
