#!/usr/bin/env python3
"""Build the complete Word presentation. Requires python-docx and Pillow."""
from pathlib import Path
import re
from datetime import date
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.section import WD_SECTION_START, WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
OUTPUT = DOCS / 'SupplyGuard-prezentare-completa.docx'
doc = Document()
normal = doc.styles['Normal']
normal.font.name = 'Calibri'
normal.font.size = Pt(11)
normal.paragraph_format.space_after = Pt(7)
normal.paragraph_format.line_spacing = 1.12
for name, size in [('Title', 34), ('Subtitle', 17), ('Heading 1', 22), ('Heading 2', 15), ('Heading 3', 12)]:
    style = doc.styles[name]
    style.font.name = 'Calibri'
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor.from_string('174778')
    style.paragraph_format.space_before = Pt(12)
    style.paragraph_format.space_after = Pt(8)


def setup(section, landscape=False):
    section.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = (Cm(29.7), Cm(21)) if landscape else (Cm(21), Cm(29.7))
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    section.header_distance = Cm(.7)
    section.footer_distance = Cm(.7)


setup(doc.sections[0])
header = doc.sections[0].header.paragraphs[0]
header.text = 'SUPPLYGUARD  |  PREZENTAREA APLICAȚIEI'
header.runs[0].font.size = Pt(8)
header.runs[0].font.color.rgb = RGBColor.from_string('64748B')
footer = doc.sections[0].footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('SupplyGuard • ')
field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE')
footer._p.append(field)
for r in footer.runs:
    r.font.size = Pt(9)


def section(landscape=False):
    s = doc.add_section(WD_SECTION_START.NEW_PAGE)
    setup(s, landscape)
    return s


def rich(p, text):
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: m[1] + (' ('+m[2]+')' if m[2].startswith('http') else ''), text)
    for part in re.split(r'(\*\*.*?\*\*|`[^`]+`)', text):
        if not part:
            continue
        run = p.add_run(part[2:-2] if part.startswith('**') else part[1:-1] if part.startswith('`') else part)
        if part.startswith('**'):
            run.bold = True
        elif part.startswith('`'):
            run.font.name = 'Consolas'; run.font.size = Pt(9)


def table(rows):
    t = doc.add_table(rows=1, cols=len(rows[0]))
    t.style = 'Table Grid'
    t.autofit = False
    total = doc.sections[-1].page_width - doc.sections[-1].left_margin - doc.sections[-1].right_margin
    # Weight columns by text length, while avoiding extremely narrow columns.
    weights = [max(8, min(48, max(len(row[i]) for row in rows))) for i in range(len(rows[0]))]
    widths = [int(total * weight / sum(weights)) for weight in weights]
    if len(rows[0]) == 10:
        weights = [1, 3.4, 1.2, 2, 2, 1.8, 5.7, 1.5, 1.5, 1.5]
        widths = [int(total*w/sum(weights)) for w in weights]
    if len(rows[0]) == 9:
        weights = [1, 2.6, 1.3, 1.9, 6, 3.4, 1.65, 1.65, 1.65]
        widths = [int(total*w/sum(weights)) for w in weights]
    for col, width in zip(t.columns, widths):
        col.width = width
    for i, values in enumerate(rows):
        cells = t.rows[0].cells if i == 0 else t.add_row().cells
        trpr = t.rows[i]._tr.get_or_add_trPr()
        cant_split = OxmlElement('w:cantSplit'); trpr.append(cant_split)
        if i == 0:
            repeat = OxmlElement('w:tblHeader'); trpr.append(repeat)
        for cell, value, width in zip(cells, values, widths):
            cell.width = width
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.line_spacing = 1.0
            rich(p, value)
            for run in p.runs:
                run.font.size = Pt(8.5 if len(values) >= 8 else 9)
                if i == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor(255,255,255)
            shade = OxmlElement('w:shd')
            shade.set(qn('w:fill'), '174778' if i == 0 else 'F0F5FA' if i%2 else 'FFFFFF')
            cell._tc.get_or_add_tcPr().append(shade)
    doc.add_paragraph()


def markdown(text, drop_title=True):
    lines = text.splitlines()
    index = 0
    in_code = False
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith('```'):
            in_code = not in_code; index += 1; continue
        if in_code:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1
            r = p.add_run(line)
            r.font.name = 'Consolas'; r.font.size = Pt(8.5)
            index += 1; continue
        if line.startswith('|'):
            rows=[]
            while index < len(lines) and lines[index].strip().startswith('|'):
                row=[c.strip() for c in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in row): rows.append(row)
                index += 1
            table(rows); continue
        if not line:
            index+=1; continue
        if line.startswith('# '):
            if not drop_title: doc.add_heading(line[2:],1)
        elif line.startswith('### '):
            doc.add_heading(line[4:],3)
        elif line.startswith('## '):
            doc.add_heading(line[3:],2)
        elif line.startswith('!['):
            pass
        else:
            style = 'List Bullet' if line.startswith('- ') else None
            value = re.sub(r'^(?:- |\d+\. )','',line) if style else line
            p = doc.add_paragraph(style=style); rich(p,value)
        index += 1


def chapter(title, landscape=False):
    section(landscape)
    doc.add_heading(title,1)


# Cover and reading guide.
doc.add_paragraph('SUPPLYGUARD', 'Title')
doc.add_paragraph('Descrierea aplicației, exemple practice,\nrezultate experimentale și capturi de ecran', 'Subtitle')
doc.add_paragraph('Documentație consolidată • 12 noiembrie 2026')
doc.add_paragraph('Versiunea software-ului: 0.1.0')
doc.add_paragraph('Aplicație desktop Python / Tkinter, cu integrare Syft și Cosign.')
doc.add_heading('Ce conține documentul',2)
for item in ['1. Descrierea exactă și funcțiile aplicației',
             '2. Exemple practice și comenzi de utilizare',
             '3. Capturi reale de ecran, cu explicații',
             '4. Rezultatele experimentale din capitolele 4 și 5',
             '5. Legătura cu lucrarea și limitele evaluării',
             '6. Fișierele rezultate și instrucțiuni de repetare']:
    doc.add_paragraph(item)
doc.add_paragraph('Documentul reunește explicațiile funcționale, cele 11 capturi PNG și valorile măsurate local. Simulările demonstrative sunt deosebite explicit de verificările criptografice reale. Documentul Word original al lucrării nu a fost modificat.')

chapter('1. Descrierea exactă și funcțiile aplicației')
text=(DOCS/'descriere-aplicatie.md').read_text().split('## Documente asociate')[0]
markdown(text)

chapter('2. Exemple practice și comenzi de utilizare')
markdown('''## 2.1 Verificarea componentelor unui SBOM
+Se execută din rădăcina proiectului. Primul exemplu este acceptat; al doilea conține componenta interzisă xz@5.6.1 și returnează intenționat codul 1.
+```bash
+python3 -m supplyguard check examples/clean.cdx.json
+python3 -m supplyguard check examples/blocked.cdx.json
+```
+| Exemplu | Rezultat observat | Cod |
+|---|---|---|
+| demo@1.0.0 | passed=true; lista findings este goală | 0 |
+| xz@5.6.1 | passed=false; componentă interzisă prin politica locală | 1 |
+
+## 2.2 Verificarea integrității unui director
+Se pornește de la un director release/ care conține fișierele aprobate. Referința se salvează separat de directorul scanat.
+```bash
+python3 -m supplyguard snapshot release --output release-baseline.json
+python3 -m supplyguard compare release --baseline release-baseline.json
+```
+În demonstrația capturată au fost inventariate două fișiere. Ulterior, application.txt a fost modificat, obsolete.txt a fost șters și new.txt a fost adăugat. Comparația a produs rezultatul următor:
+```json
+{
+  "added": ["new.txt"],
+  "removed": ["obsolete.txt"],
+  "changed": ["application.txt"]
+}
+```
+Codul de ieșire a fost 1, deoarece directorul diferă de referință.
+
+## 2.3 Generarea SBOM-ului
+```bash
+python3 -m supplyguard sbom dir:release --output release.cdx.json
+python3 -m supplyguard check release.cdx.json --policy policy.json
+```
+Prima comandă necesită Syft instalat și produce inventarul. A doua aplică politica locală. Completitudinea inventarului depinde de sursa scanată și de configurația Syft, conform rezultatelor experimentale.
+
+## 2.4 Semnarea și verificarea unui fișier
+```bash
+python3 -m supplyguard sign release/application.tar.gz --bundle application.sigstore.json
+python3 -m supplyguard verify release/application.tar.gz --bundle application.sigstore.json --identity 'release@example.org' --issuer 'https://accounts.google.com'
+```
+Acesta este un exemplu de sintaxă pentru fluxul keyless, nu o autentificare OIDC executată pentru capturi. Identitatea și issuer-ul se înlocuiesc cu valorile aprobate efectiv. Semnarea poate deschide browserul și publică datele semnării în jurnalul Sigstore. Experimentul T0–T6 din acest document folosește separat chei locale.
+
+## 2.5 Laboratoare demonstrative
+```bash
+python3 -m supplyguard simulate solarwinds
+python3 -m supplyguard simulate xz
+```
+Primul scenariu raportează application.txt modificat, iar al doilea release-only.m4 adăugat. Ambele au produs detected=true. Fișierele sunt temporare și inofensive.
+
+## 2.6 Experimentele complete E1/E2
+```bash
+python3 -m supplyguard experiment --prepare
+```
+Prima pregătire descarcă sursele oficiale și versiunile Syft verificate prin checksum. Instalările npm folosesc --ignore-scripts. Sunt executate scanările A–I, completarea hash-urilor, verificarea independentă a arhivei accepts, scenariile T0–T6 și măsurătorile de performanță.
+'''.replace('\n+','\n'))

# Each screenshot receives its own page; wide tables use landscape orientation.
gallery=(DOCS/'prezentare-software-cu-capturi.md').read_text()
gallery=gallery.split('## Capturi și explicații',1)[1].split('## Cum este construit software-ul',1)[0]
blocks=re.split(r'(?=### Figura \d+)',gallery)
for block in blocks:
    match=re.search(r'### Figura (\d+) — ([^\n]+)',block)
    if not match: continue
    number=int(match.group(1)); landscape=number in (6,7,8,9)
    section(landscape)
    if number == 1: doc.add_heading('3. Capturi reale de ecran',1)
    doc.add_heading(f'Figura {number} — {match.group(2)}',2)
    image=re.search(r'!\[[^\]]*\]\(([^)]+)\)',block)
    picture_path=DOCS/image.group(1)
    with Image.open(picture_path) as picture:
        ratio=picture.height/picture.width
    width=Cm(25.8 if landscape else 17.1)
    max_height=Cm(9 if landscape else 12)
    width=min(width,int(max_height/ratio))
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(picture_path),width=width)
    p.paragraph_format.keep_with_next=True
    cap=doc.add_paragraph(f'Captură reală a aplicației • {picture_path.name}')
    cap.paragraph_format.space_after=Pt(8)
    for r in cap.runs: r.italic=True; r.font.size=Pt(8)
    rest=block[image.end():].strip()
    # Keep explanatory tables in the examples/results chapters, avoiding an oversized figure page.
    if number==6:
        rest=rest.split('| Rezultat măsurat')[0]+'\n\nRezultate: 0 componente npm fără lockfile; 65 + rădăcina implicit; 368 + rădăcina cu dezvoltarea activată. Acoperirea este calculată din perechi unice nume–versiune, cu rădăcina exclusă din numitor. Tabelul complet este inclus în capitolul 4.'
    if number==9:
        rest=rest.split('| Scenariu')[0]+'\n\nT0, T4 și T6 sunt acceptate; T1, T2, T3 și T5 sunt respinse. T6 arată că un artefact modificat înainte de semnarea legitimă poate avea semnătură validă. Tabelul complet și interpretarea sunt incluse în capitolul 4.'
    markdown(rest)

chapter('4. Rezultatele experimentale din capitolele 4 și 5',landscape=True)
markdown((DOCS/'experimente-capitole-4-5.md').read_text())

chapter('5. Legătura cu lucrarea și limitele evaluării')
analysis=(DOCS/'analiza-capitole-4-5.md').read_text().split('## Rulare și consultare')[0]
markdown(analysis)

chapter('6. Fișierele rezultate și instrucțiuni de repetare')
markdown('''## 6.1 Livrabile
+| Fișier / director | Conținut |
+|---|---|
+| docs/SupplyGuard-prezentare-completa.docx | Documentul Word de față, cu imaginile încorporate. |
+| docs/capturi/ | Cele 11 imagini PNG originale din aplicație. |
+| docs/rezultate-experimente/ | Tabele CSV pentru Express, Flask, hash-uri și scenariile Cosign. |
+| build/experiments/measurements.json | Valorile experimentale și mediul măsurat. |
+| build/experiments/commands.log | Comenzile executate, codurile și ieșirile proceselor. |
+| build/experiments/reference-package-lock.json | Referința Express păstrată pentru repetarea experimentului. |
+| build/experiments/A.cdx.json … I.cdx.json | SBOM-urile brute produse de scanări. |
+| build/experiments/E-hashes.cdx.json și F-hashes.cdx.json | SBOM-urile completate cu hash-uri. |
+
+## 6.2 Pornirea interfeței
+```bash
+.venv/bin/python -m supplyguard.gui
+```
+Interfața necesită Python cu Tkinter. Pentru capturile din această sesiune, Tkinter și BLT au fost extrase temporar în /tmp; nu au fost instalate permanent în sistem. Pe Ubuntu/Debian, instalarea obișnuită se face prin pachetul python3-tk. Syft și Cosign sunt necesare pentru operațiunile care le apelează.
+
+## 6.3 Repetarea experimentelor
+```bash
+# Prima pregătire și execuție
+python3 -m supplyguard experiment --prepare
+
+# Repetare cu sursele și uneltele deja pregătite
+python3 -m supplyguard experiment
+
+# Regenerarea tabelelor fără scanări sau instalări
+python3 scripts/reproduce_chapters.py --report-only
+
+# Verificările automate
+python3 -m unittest discover -s tests -v
+```
+Fluxul experimental necesită Python 3.11+, npm și Cosign în .venv/bin/cosign. Repetarea experimentelor poate accesa registrele npm/PyPI și arhiva accepts; regenerarea raportului folosește măsurătorile locale.
+
+## 6.4 Validarea efectuată
+Au trecut 18 din 18 teste automate. Pentru capturi au fost rulate verificările SBOM acceptat/blocat, cele două simulări, crearea inventarului și compararea cu intervenții controlate. Ferestrele cu rezultate Express, Flask și Cosign au fost deschise și capturate din aplicația reală.
+
+## 6.5 Surse și trasabilitate
+Documentul consolidează fișierele locale descriere-aplicatie.md, prezentare-software-cu-capturi.md, experimente-capitole-4-5.md și analiza-capitole-4-5.md. Rezultatele provin din rulările locale ale proiectului, nu din copierea valorilor așteptate din lucrare.
+
+Documentație oficială Syft: https://oss.anchore.com/docs/reference/syft/configuration/
+
+Documentație oficială Cosign: https://docs.sigstore.dev/cosign/signing/signing_with_blobs/
+'''.replace('\n+','\n'))

doc.core_properties.title='SupplyGuard — prezentarea completă a aplicației'
doc.core_properties.subject='Funcții, exemple, capturi și rezultate experimentale E1/E2'
doc.core_properties.author='SupplyGuard'
doc.core_properties.keywords='SupplyGuard, SBOM, Syft, Cosign, Express, Flask, integritate'
doc.save(OUTPUT)
print(OUTPUT)
print('Images:',len(doc.inline_shapes),'Tables:',len(doc.tables),'Sections:',len(doc.sections))
