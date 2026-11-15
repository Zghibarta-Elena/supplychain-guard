#!/usr/bin/env python3
"""Run thesis E1/E2 on real projects. Network is needed for preparation only.

Outputs live under build/experiments; reports contain measured, not preset values.
Requires Python 3.11+, npm, and the project's .venv/bin/cosign.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tarfile
import time
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build/experiments'
REPORT = ROOT / 'docs/experimente-capitole-4-5.md'


def fetch(url, target):
    print('Download:', url, flush=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        target.write_bytes(response.read())


def run(args, cwd=None, env=None, allowed=(0,)):
    result = subprocess.run([str(a) for a in args], cwd=cwd, env=env,
                            capture_output=True, text=True)
    with (WORK / 'commands.log').open('a') as log:
        log.write(f'cwd={cwd}\n{args}\nexit={result.returncode}\n{result.stdout}\n{result.stderr}\n')
    if result.returncode not in allowed:
        raise RuntimeError(f'{args}: {result.stderr[-3000:]} {result.stdout[-1000:]}')
    return result


def prepare():
    tools = WORK / 'tools'
    tools.mkdir(parents=True, exist_ok=True)
    for version in ('1.18.1', '1.56.0'):
        target = tools / f'syft-{version}'
        if target.exists():
            continue
        name = f'syft_{version}_linux_amd64.tar.gz'
        archive = tools / name
        sums = tools / f'{version}-checksums.txt'
        base = f'https://github.com/anchore/syft/releases/download/v{version}'
        fetch(f'{base}/{name}', archive)
        fetch(f'{base}/syft_{version}_checksums.txt', sums)
        expected = next(line.split()[0] for line in sums.read_text().splitlines() if line.split()[-1] == name)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError('Syft archive checksum mismatch')
        with tarfile.open(archive) as tar:
            target.write_bytes(tar.extractfile('syft').read())
        target.chmod(0o755)
    for project, repo, tag in [('express', 'expressjs/express', 'v5.1.0'),
                               ('flask', 'pallets/flask', '3.1.1')]:
        dest = WORK / project
        if dest.exists():
            continue
        archive = WORK / f'{project}-source.tgz'
        fetch(f'https://codeload.github.com/{repo}/tar.gz/refs/tags/{tag}', archive)
        dest.mkdir()
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts[1:]
                if not parts:
                    continue
                path = dest.joinpath(*parts)
                if not path.resolve().is_relative_to(dest.resolve()):
                    raise ValueError('Unsafe archive path')
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(tar.extractfile(member).read())


def components(doc):
    result = []
    def visit(items):
        for item in items:
            result.append(item)
            visit(item.get('components', []))
    visit(doc.get('components', []))
    return result


def identity(comp):
    name = comp['name']
    if comp.get('group') and not name.startswith(comp['group'] + '/'):
        name = comp['group'] + '/' + name
    return name, comp.get('version', '')


def npm_reference(lock):
    all_packages, prod = set(), set()
    for path, meta in lock['packages'].items():
        if not path or not meta.get('version'):
            continue
        pair = (meta.get('name') or path.rsplit('node_modules/', 1)[-1], meta['version'])
        all_packages.add(pair)
        if not meta.get('dev'):
            prod.add(pair)
    return all_packages, prod


def percent(count, total):
    return f'{100 * count / total:.1f}%' if total else '–'


def metadata_rates(items):
    return [percent(sum(bool(c.get(key)) for c in items), len(items))
            for key in ('purl', 'hashes', 'licenses')]


def add_hashes(doc, lock):
    index = {}
    for path, meta in lock['packages'].items():
        if path and meta.get('integrity'):
            pair = (meta.get('name') or path.rsplit('node_modules/', 1)[-1], meta.get('version'))
            index.setdefault(pair, set()).add(meta['integrity'])
    count = 0
    for comp in components(doc):
        if not comp.get('purl', '').startswith('pkg:npm/') or comp.get('hashes'):
            continue
        candidates = index.get(identity(comp), set())
        if len(candidates) != 1:
            continue  # Do not guess if a name/version has conflicting integrities.
        hashes = []
        for token in next(iter(candidates)).split():
            algorithm, value = token.split('-', 1)
            size = {'sha512': 64, 'sha384': 48, 'sha256': 32, 'sha1': 20}.get(algorithm)
            if size:
                digest = base64.b64decode(value.split('?', 1)[0], validate=True)
                if len(digest) != size:
                    raise ValueError('Invalid SRI digest length')
                hashes.append({'alg': {'sha1': 'SHA-1'}.get(algorithm, 'SHA-' + algorithm[3:]),
                               'content': digest.hex()})
        if hashes:
            comp['hashes'] = hashes
            count += 1
    return count


def scan(label, project, version, dev=False):
    print('Scan:', label, version, flush=True)
    env = os.environ.copy()
    env['SYFT_CHECK_FOR_APP_UPDATE'] = 'false'
    env['SYFT_JAVASCRIPT_INCLUDE_DEV_DEPENDENCIES'] = str(dev).lower()
    output = WORK / f'{label}.cdx.json'
    run([WORK / f'tools/syft-{version}', f'dir:{project}', '-o', f'cyclonedx-json={output}'], env=env)
    return json.loads(output.read_text())


def e1():
    express, flask = WORK / 'express', WORK / 'flask'
    if (express / 'node_modules').exists():
        shutil.rmtree(express / 'node_modules')
    (express / 'package-lock.json').unlink(missing_ok=True)
    a = scan('A', express, '1.18.1')
    lock_archive = WORK / 'reference-package-lock.json'
    if lock_archive.exists():
        shutil.copyfile(lock_archive, express / 'package-lock.json')
    else:
        run(['npm', 'install', '--ignore-scripts', '--package-lock-only', '--no-audit', '--no-fund'], cwd=express)
        shutil.copyfile(express / 'package-lock.json', lock_archive)
    lock = json.loads(lock_archive.read_text())
    all_ref, prod_ref = npm_reference(lock)
    docs = [('A', 'Sursă, fără lockfile', '1.18.1', a)]
    docs.append(('B', 'Sursă, cu lockfile', '1.18.1', scan('B', express, '1.18.1')))
    run(['npm', 'ci', '--ignore-scripts', '--omit=dev', '--no-audit', '--no-fund'], cwd=express)
    docs.append(('C', 'După npm ci --omit=dev', '1.18.1', scan('C', express, '1.18.1')))
    run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=express)
    for label, moment, version, dev in [('D', 'După npm ci complet', '1.18.1', False),
                                        ('E', 'Ca D, inclusiv dezvoltare', '1.18.1', True),
                                        ('F', 'Ca D', '1.56.0', False)]:
        docs.append((label, moment, version, scan(label, express, version, dev)))
    rows, hashes = [], []
    for label, moment, version, doc in docs:
        items = components(doc)
        npm_all = [c for c in items if c.get('purl', '').startswith('pkg:npm/')]
        npm = [c for c in npm_all if identity(c) != ('express', '5.1.0')]
        actual = {identity(c) for c in npm}
        actions = [c for c in items if c.get('purl', '').startswith('pkg:github/')]
        foreign = [c for c in items if c not in npm_all]
        root_suffix = ' + rădăcina' if len(npm_all) > len(npm) else ''
        rows.append([label, moment, version, str(len(npm)) + root_suffix,
                     percent(len(actual & prod_ref), len(prod_ref)),
                     percent(len(actual & all_ref), len(all_ref)),
                     f'{len(actions)} GitHub; {len(foreign)} total în afara npm', *metadata_rates(npm)])
        if label in ('E', 'F'):
            added = add_hashes(doc, lock)
            output = WORK / f'{label}-hashes.cdx.json'
            output.write_text(json.dumps(doc, indent=2))
            hashes.append([label, len(npm), added, metadata_rates(npm)[1]])
    # Independently check a registry tarball against its added SHA-512.
    accepts = next(c for c in components(docs[4][3]) if c['name'] == 'accepts')
    pair = identity(accepts)
    meta = next(m for p, m in lock['packages'].items()
                if p.rsplit('node_modules/', 1)[-1] == pair[0] and m.get('version') == pair[1])
    archive = WORK / 'accepts.tgz'
    fetch(meta['resolved'], archive)
    sha = hashlib.sha512(archive.read_bytes()).hexdigest()
    hash_ok = any(h['alg'] == 'SHA-512' and h['content'] == sha for h in accepts.get('hashes', []))
    if not hash_ok:
        raise ValueError('Independent accepts hash verification failed')
    # Build a pinned runtime environment using wheel distributions only.
    venv = WORK / 'flask-venv'
    if not venv.exists():
        run(['python3', '-m', 'venv', venv])
    pins = ['Flask==3.1.1', 'blinker==1.9.0', 'click==8.2.1', 'itsdangerous==2.2.0',
            'Jinja2==3.1.6', 'MarkupSafe==3.0.2', 'Werkzeug==3.1.3']
    run([venv / 'bin/python', '-m', 'pip', 'install', '--only-binary=:all:', *pins])
    # Remove setuptools if injected by the host venv implementation.
    run([venv / 'bin/python', '-m', 'pip', 'uninstall', '-y', 'setuptools'])
    runtime = {(p.split('==')[0].lower().replace('_', '-'), p.split('==')[1]) for p in pins}
    uv = tomllib.loads((flask / 'uv.lock').read_text())
    uv_ref = {(p['name'].lower().replace('_', '-'), p['version']) for p in uv['package']}
    flask_rows = []
    for label, source, version in [('G', flask, '1.18.1'), ('H', flask, '1.56.0'), ('I', venv, '1.18.1')]:
        doc = scan(label, source, version)
        items = [c for c in components(doc) if c.get('purl', '').startswith('pkg:pypi/')]
        actual = {(c['name'].lower().replace('_', '-'), c.get('version')) for c in items}
        flask_rows.append([label, 'Mediu virtual instalat' if label == 'I' else 'Sursă repository', version,
                           len(items), f'{len(actual & uv_ref)} din uv.lock (perechi unice)',
                           f'{len(actual & runtime)} din {len(runtime)}', *metadata_rates(items)])
    return rows, flask_rows, hashes, {'npm_total': len(all_ref), 'npm_prod': len(prod_ref),
                                     'lock_entries': len(lock['packages']) - 1, 'uv_total': len(uv_ref),
                                     'accepts': pair, 'accepts_sha512': sha, 'hash_ok': hash_ok}


def e2():
    directory = WORK / 'sigstore'
    directory.mkdir(exist_ok=True)
    cosign = ROOT / '.venv/bin/cosign'
    env = os.environ.copy()
    env['COSIGN_PASSWORD'] = ''  # Disposable experiment keys only.
    for name in ('legitimate', 'attacker'):
        if not (directory / f'{name}.key').exists():
            run([cosign, 'generate-key-pair', '--output-key-prefix', name], cwd=directory, env=env)
        (directory / f'{name}.key').chmod(0o600)
    artifact = directory / 'release.tgz'
    def archive(injected=False):
        with tarfile.open(artifact, 'w:gz') as tar:
            for path in sorted((WORK / 'express').rglob('*')):
                rel = path.relative_to(WORK / 'express')
                if path.is_file() and 'node_modules' not in rel.parts and rel.name != 'package-lock.json':
                    tar.add(path, arcname=str(rel), recursive=False)
            if injected:
                data = b'Harmless experimental marker added before signing\n'
                info = tarfile.TarInfo('EXPERIMENT-MARKER.txt')
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    archive()
    original = artifact.read_bytes()
    sbom = WORK / 'E.cdx.json'
    def sign(path, key, bundle):
        return run([cosign, 'sign-blob', '--yes', '--key', directory / f'{key}.key',
                    '--use-signing-config=false', '--tlog-upload=false', '--bundle', bundle, path], env=env)
    def verify(path, key, bundle):
        return run([cosign, 'verify-blob', '--key', directory / f'{key}.pub',
                    '--insecure-ignore-tlog=true', '--offline=true', '--bundle', bundle, path],
                   env=env, allowed=(0, 1))
    legit_bundle, attacker_bundle = directory / 'release.bundle.json', directory / 'attacker.bundle.json'
    sbom_bundle = directory / 'sbom.bundle.json'
    sign(artifact, 'legitimate', legit_bundle)
    sign(sbom, 'legitimate', sbom_bundle)
    rows = []
    def record(label, change, key, bundle, expected):
        result = verify(artifact, key, bundle)
        accepted = result.returncode == 0
        rows.append([label, change, 'Legitimă' if key == 'legitimate' else 'Atacator',
                     'Acceptat' if accepted else 'Respins', result.returncode,
                     'Da' if accepted == expected else 'NU'])
        if accepted != expected:
            raise RuntimeError(f'Unexpected cryptographic result: {label}')
    record('T0', 'Nimic (control)', 'legitimate', legit_bundle, True)
    data = bytearray(original); data[1000] ^= 1; artifact.write_bytes(data)
    record('T1', 'Un octet modificat în arhivă', 'legitimate', legit_bundle, False)
    archive(True)
    record('T2', 'Arhivă reconstruită cu marker; semnătură veche', 'legitimate', legit_bundle, False)
    sign(artifact, 'attacker', attacker_bundle)
    record('T3', 'Arhivă modificată, semnată de atacator', 'legitimate', attacker_bundle, False)
    record('T4', 'Ca T3, verificare cu cheia atacatorului', 'attacker', attacker_bundle, True)
    artifact.write_bytes(original)
    record('T5', 'Bundle-ul SBOM-ului atașat arhivei', 'legitimate', sbom_bundle, False)
    archive(True)
    modified_bundle = directory / 'modified-legitimate.bundle.json'
    sign(artifact, 'legitimate', modified_bundle)
    record('T6', 'Marker introdus înaintea semnării legitime', 'legitimate', modified_bundle, True)
    times = {'sign': [], 'verify': []}
    for _ in range(20):
        start = time.perf_counter()
        sign(artifact, 'legitimate', modified_bundle)
        times['sign'].append(1000 * (time.perf_counter() - start))
        start = time.perf_counter()
        verify(artifact, 'legitimate', modified_bundle)
        times['verify'].append(1000 * (time.perf_counter() - start))
    return rows, {'artifact_bytes': len(original), 'sbom_bytes': sbom.stat().st_size,
                  'cosign': run([cosign, 'version']).stdout,
                  'timings_ms': times, 'means_ms': {k: statistics.mean(v) for k, v in times.items()}}


def table(headers, rows):
    def cell(v):
        return str(v).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join('| ' + ' | '.join(map(cell, row)) + ' |'
                     for row in [headers, ['---'] * len(headers), *rows])


def report(data):
    ref, sig = data['reference'], data['sigstore']
    # Derive provenance from Syft location properties rather than assuming it.
    for row in data['flask']:
        doc = json.loads((WORK / f'{row[0]}.cdx.json').read_text())
        origins = {}
        for comp in components(doc):
            if not comp.get('purl', '').startswith('pkg:pypi/'):
                continue
            path = next((p['value'] for p in comp.get('properties', [])
                         if p['name'] == 'syft:location:0:path'), '?')
            source = 'mediu instalat' if 'site-packages/' in path else path.lstrip('/')
            origins[source] = origins.get(source, 0) + 1
        row[4] = '; '.join(f'{count} din {source}' for source, count in origins.items())
    for row in data['express']:
        doc = json.loads((WORK / f'{row[0]}.cdx.json').read_text())
        items = components(doc)
        actions = [c for c in items if c.get('purl', '').startswith('pkg:github/')]
        files = [c for c in items if c.get('type') == 'file']
        row[6] = f'{len(actions)} acțiuni GitHub ({len({c.get("purl") for c in actions})} unice)'
        if files:
            row[6] += f'; {len(files)} intrări de tip fișier separat'
    text = f'''# Rezultate experimentale — capitolele 4 și 5

Acest raport este generat din rulări reale prin `python3 scripts/reproduce_chapters.py`.
Data rulării: {time.strftime('%Y-%m-%d %H:%M:%S %z')}. Metadatele și măsurătorile brute sunt în `build/experiments/measurements.json`, iar comenzile și ieșirile în `build/experiments/commands.log`.

## Metodă și diferențe față de documentul Word

Proiecte: Express v5.1.0 și Flask 3.1.1, arhive oficiale GitHub. Syft: 1.18.1 și 1.56.0, arhive verificate SHA-256 față de checksum-urile publicate. Instalarea npm folosește `--ignore-scripts`; mediul Flask folosește numai wheel-uri și șapte versiuni fixate. Cheile Cosign sunt locale, temporare pentru experiment, fără OIDC și fără jurnal public.

Mediul efectiv și versiunile sunt în tabelul următor. Lockfile-ul Express este generat la prima rulare și păstrat pentru repetări. Rezolvarea dependențelor la o altă dată poate modifica referința față de lucrare. Numărul componentelor este numărul intrărilor CycloneDX; acoperirea se calculează prin intersecția perechilor unice nume–versiune cu referința, nu prin împărțirea simplă a numărului de componente. Rădăcina Express este afișată separat și exclusă din numitorul procentelor. Procentele PURL/hash/licență au ca numitor dependențele ecosistemului vizat.

{table(['Element', 'Valoare măsurată'], data['environment'].items())}

## 4.3 Rezultate

**Tabelul 4.1 – Express 5.1.0 (npm), referință măsurată: {ref['npm_prod']} pachete de producție, {ref['npm_total']} în total; {ref['lock_entries']} intrări de lockfile**

{table(['Cfg.', 'Momentul generării', 'Syft', 'Componente npm', 'Acoperire producție', 'Acoperire totală', 'Componente străine', 'Cu PURL', 'Cu hash', 'Cu licență'], data['express'])}

**Tabelul 4.2 – Flask 3.1.1 (PyPI), referință: {ref['uv_total']} perechi în uv.lock și 7 pachete de rulare fixate**

{table(['Cfg.', 'Momentul generării', 'Syft', 'Componente PyPI', 'Potriviri cu referința', 'Versiuni corecte de rulare', 'Cu PURL', 'Cu hash', 'Cu licență'], data['flask'])}

## 4.4 Interpretarea rezultatelor

Tabelele permit compararea prezenței lockfile-ului (A/B), instalării dependențelor (B/C/D), includerii dezvoltării (D/E), versiunii generatorului (D/F și G/H) și mediului instalat (G/I). O componentă cu nume corect și versiune greșită nu contribuie la acoperire. Componentele GitHub sunt raportate separat de npm; potrivirile PyPI sunt comparate cu uv.lock și cu mediul de rulare. Rezultatele descriu aceste versiuni și această rezolvare a dependențelor, nu toate proiectele npm sau PyPI.

**R1. Lockfile-ul schimbă inventarul din sursă.** În A sunt {data['express'][0][3]} componente npm, iar în B sunt {data['express'][1][3]}. Acțiunile GitHub nu substituie inventarul dependențelor npm.

**R2. Dezvoltarea trebuie inclusă explicit.** D are acoperire totală {data['express'][3][5]}, iar E are {data['express'][4][5]}. Diferența dintre referința totală și cea de producție este de {ref['npm_total'] - ref['npm_prod']} perechi nume–versiune.

**R3. Hash-urile lipsesc înainte de post-procesare.** În E, procentul măsurat este {data['express'][4][-2]}. Completarea din lockfile este prezentată separat în 4.5, excluzând rădăcina proiectului, care nu are o arhivă de dependență în lockfile.

**R4. Domeniul scanării introduce componente suplimentare.** G include {data['flask'][0][3]} componente din exemplul Celery; H include și pachetele uv.lock. În F, cele 9 intrări suplimentare de tip fișier nu sunt pachete npm și nu sunt numărate drept acțiuni GitHub.

**R5. Mediul influențează metadatele.** I identifică {data['flask'][2][5]} versiuni de rulare corecte, dar numai {data['flask'][2][-1]} componente cu licență. Documentul Word raporta 62,5%; rularea actuală folosește alt Python/pip și versiuni de rulare fixate explicit. Această diferență nu a fost eliminată prin ajustarea artificială a rezultatului. Timpii Cosign și dimensiunile artefactelor diferă, de asemenea, față de document.

## 4.5 Completarea hash-urilor

Hash-urile SRI din lockfile sunt convertite din Base64 în hexazecimal și adăugate componentelor npm cu aceeași pereche nume–versiune. Intrările ambigue nu sunt completate automat. Hash-urile existente nu sunt înlocuite. Hash-ul arhivei de pachet nu este hash-ul unui director instalat.

{table(['Configurație', 'Componente npm', 'Componente completate', 'Cu hash după completare'], data['hashes'])}

Verificare independentă: arhiva npm pentru `{ref['accepts'][0]}@{ref['accepts'][1]}` a fost descărcată și SHA-512 calculat local coincide cu hash-ul adăugat: **{ref['hash_ok']}**. SHA-512: `{ref['accepts_sha512']}`.

## 5.3 Rezultate — semnare cu cheie, fără jurnal

Artefactul de control are {sig['artifact_bytes']} octeți, iar SBOM-ul {sig['sbom_bytes']} octeți. Markerul introdus în T2/T6 este text inofensiv. Testele folosesc operații criptografice Cosign reale. Cheia legitimă și cheia atacatorului sunt distincte. Dezactivarea jurnalului este limitată la acest experiment cu chei locale.

**Tabelul 5.1 – Scenarii și rezultatul verificării**

{table(['Scenariu', 'Ce s-a modificat', 'Cheia de verificare', 'Rezultat', 'Cod', 'Conform așteptării'], data['scenarios'])}

**Performanță – 20 de rulări pentru fiecare operație, timp real incluzând pornirea procesului**

{table(['Operație', 'Rulări', 'Media (ms)', 'Minim (ms)', 'Maxim (ms)'], [[k, len(v), f'{statistics.mean(v):.2f}', f'{min(v):.2f}', f'{max(v):.2f}'] for k, v in sig['timings_ms'].items()])}

## 5.4 Interpretarea rezultatelor

T0 este controlul pozitiv. T1 și T2 testează alterarea după semnare, T3 cheia neautorizată, iar T5 asocierea unui bundle cu alt artefact. T4 arată efectul configurării verificatorului să aibă încredere în cheia atacatorului. T6 arată că o semnătură validă poate acoperi un artefact modificat înainte de semnare. Experimentul nu măsoară OIDC, Fulcio, Rekor, verificarea provenienței sau atestări OCI.

## Recomandări

1. Păstrați lockfile-ul folosit drept referință și versiunea generatorului lângă rezultate.
2. Evaluați separat inventarul produsului și inventarul mediului de build, incluzând dezvoltarea explicit când este necesar.
3. Folosiți intersecția nume–versiune pentru acoperire și raportați componentele străine separat.
4. Completați hash-urile dintr-o sursă verificată și păstrați distincția dintre hash de arhivă și hash de fișier.
5. Verificați cu cheia sau identitatea aprobată înainte de deployment; semnarea se completează cu verificarea procesului de build.

Documentație oficială: [configurația Syft](https://oss.anchore.com/docs/reference/syft/configuration/), [semnarea fișierelor cu Cosign](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/).
'''
    REPORT.write_text(text)
    (WORK / 'measurements.json').write_text(json.dumps(data, indent=2))
    export_dir = ROOT / 'docs/rezultate-experimente'
    export_dir.mkdir(exist_ok=True)
    headers = {
        'express': ['Cfg.', 'Moment', 'Syft', 'Componente npm', 'Acoperire producție', 'Acoperire totală', 'Componente străine', 'Cu PURL', 'Cu hash', 'Cu licență'],
        'flask': ['Cfg.', 'Moment', 'Syft', 'Componente PyPI', 'Sursă', 'Versiuni corecte', 'Cu PURL', 'Cu hash', 'Cu licență'],
        'hashes': ['Cfg.', 'Componente npm', 'Completate', 'Cu hash după completare'],
        'scenarios': ['Scenariu', 'Modificare', 'Cheie', 'Rezultat', 'Cod', 'Conform așteptării']}
    for name in ('express', 'flask', 'hashes', 'scenarios'):
        for directory in (WORK, export_dir):
            with (directory / f'{name}.csv').open('w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers[name])
                writer.writerows(data[name])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Download sources and checked Syft binaries')
    parser.add_argument('--report-only', action='store_true', help='Regenerate tables from saved measurements and SBOMs')
    args = parser.parse_args(argv)
    WORK.mkdir(parents=True, exist_ok=True)
    if args.report_only:
        data = json.loads((WORK / 'measurements.json').read_text())
        # Recalculate npm metrics from raw SBOMs, keeping project root separate.
        for row in data['express']:
            doc = json.loads((WORK / f'{row[0]}.cdx.json').read_text())
            npm_all = [c for c in components(doc) if c.get('purl', '').startswith('pkg:npm/')]
            npm = [c for c in npm_all if identity(c) != ('express', '5.1.0')]
            row[3] = str(len(npm)) + (' + rădăcina' if len(npm_all) > len(npm) else '')
            row[-3:] = metadata_rates(npm)
        for row in data['hashes']:
            doc = json.loads((WORK / f'{row[0]}-hashes.cdx.json').read_text())
            npm = [c for c in components(doc) if c.get('purl', '').startswith('pkg:npm/')
                   and identity(c) != ('express', '5.1.0')]
            row[1] = len(npm)
            row[3] = metadata_rates(npm)[1]
        (WORK / 'measurements.json').write_text(json.dumps(data, indent=2))
        report(data)
        return
    if args.prepare:
        prepare()
    express, flask, hashes, reference = e1()
    scenarios, sigstore = e2()
    environment = {}
    for name, cmd in [('Node', ['node', '--version']), ('npm', ['npm', '--version']),
                      ('Python', ['python3', '--version']), ('Sistem', ['uname', '-sm'])]:
        environment[name] = run(cmd).stdout.strip()
    environment['Cosign'] = next(line for line in sigstore['cosign'].splitlines() if 'GitVersion:' in line).strip()
    data = dict(express=express, flask=flask, hashes=hashes, reference=reference,
                scenarios=scenarios, sigstore=sigstore, environment=environment)
    (WORK / 'measurements.json').write_text(json.dumps(data, indent=2))
    report(data)
    print('Raport:', REPORT, flush=True)


if __name__ == '__main__':
    main()
