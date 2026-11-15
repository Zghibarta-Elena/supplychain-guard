# Analiza capitolelor 4 și 5 și implementarea în SupplyGuard

Sursă analizată: documentul Word „Securitatea lanțului de aprovizionare software analiza atacurilor SolarWinds și”, capitolele 4 și 5. Documentul original nu a fost modificat.

## Ce cer capitolele

Capitolul 4 descrie experimentul E1 pe proiecte reale, cu nouă configurații A–I. Măsurarea relevantă este completitudinea SBOM-ului în raport cu dependențele de referință. Capitolul 5 descrie experimentul E2: semnare cu două chei distincte, șapte scenarii T0–T6 și măsurarea duratei operațiilor. Verificările demonstrative pe un singur pachet și modificările de fișiere text, implementate inițial, nu sunt suficiente pentru aceste capitole.

| Cerință din document | Situația inițială | Implementarea adăugată |
|---|---|---|
| Express 5.1.0, configurațiile A–F | Nu existau experimente pe Express. | Descărcarea tag-ului oficial, generarea și păstrarea lockfile-ului, scanări înainte/după instalare și cu dezvoltarea activată. |
| Flask 3.1.1, configurațiile G–I | Nu existau experimente pe Flask. | Scanarea sursei și a mediului virtual cu șapte pachete de rulare fixate. |
| Syft 1.18.1 și 1.56.0 | Integrarea folosea Syft disponibil în PATH. | Descărcarea separată a celor două versiuni și verificarea SHA-256 a arhivelor față de checksum-urile publicate. |
| Acoperire și metadate | Verificarea politicii nu calcula acoperirea. | Intersecția perechilor nume–versiune cu referința; procente pentru PURL, hash și licență. |
| Componente străine | Fără clasificare în raport. | Raportarea acțiunilor GitHub, a intrărilor de tip fișier și a sursei componentelor PyPI. |
| Completarea hash-urilor | SHA-256 exista numai pentru inventarul de fișiere. | Completarea hash-urilor componentelor npm din integrity/SRI, fără înlocuirea celor existente sau alegerea arbitrară între integrități conflictuale. |
| Verificare independentă SHA-512 | Neexecutată. | Descărcarea arhivei accepts și compararea SHA-512 calculat local cu hash-ul completat. |
| Cosign offline cu cheie | CLI-ul inițial suporta semnare keyless. | Flux experimental separat, cu cheie legitimă și cheie de atacator, fără jurnal. |
| T0–T6 | Nu existau verificări criptografice pentru aceste scenarii. | Semnări și verificări Cosign reale pentru toate cele șapte scenarii. |
| Performanță | Nemăsurată. | 20 de semnări și 20 de verificări; raportarea mediei, minimului și maximului. |
| Rezultate tabelare | Tabel generic indicator–valoare. | Raport Markdown, CSV-uri și fereastră GUI cu tabele separate Express, Flask, hash-uri și Cosign. |

## Rezultatul reproducerii

Rezultatele complete sunt în [raportul experimental](experimente-capitole-4-5.md).

| Observație | Document Word | Rulare locală |
|---|---|---|
| Referință Express | 65 producție; 368 total | Reprodus: 65 și 368. |
| Express fără lockfile | 0 npm | Reprodus. |
| Express implicit | 65 + rădăcina; 17,7% acoperire totală | Reprodus. |
| Express cu dezvoltarea activată | 368 + rădăcina; 100% acoperire | Reprodus. |
| Flask sursă, Syft vechi/nou | 21 / 104 componente | Reprodus. |
| Flask instalat | 8 componente; 7/7 versiuni de rulare | Reprodus. |
| Licențe Flask instalat | 62,5% | 50%; mediul Python/pip și selecția explicită a versiunilor diferă. |
| Hash-uri completate E/F | 368 / 65 dependențe | Reprodus; rădăcina proiectului este exclusă din numitor. |
| Scenarii Cosign | T0, T4, T6 acceptate; restul respinse | Reprodus prin operații criptografice reale. |
| Versiune Cosign | 3.0.5 | 3.1.4; diferență consemnată în raport. |
| Timpi și dimensiuni artefacte | Valorile măsurate în mediul lucrării | Măsurători noi; nu sunt forțate să coincidă. |

## Precizări de metodă

1. Afirmația „fără lockfile un SBOM din sursă este gol” trebuie limitată la componentele npm și configurația A. SBOM-ul conține în continuare acțiuni GitHub.
2. Prezența unor componente în SBOM nu demonstrează validarea schemei CycloneDX. Experimentul adăugat nu rulează un validator complet de schemă.
3. Acoperirea se calculează din potriviri de nume și versiune, cu deduplicarea referinței; componentele străine și rădăcina nu măresc artificial acoperirea.
4. În Syft 1.56.0, ieșirea Express include și nouă intrări de tip fișier. Acestea trebuie deosebite de pachete și acțiuni GitHub.
5. „Cu licență” măsoară existența metadatelor de licență în SBOM. Nu reprezintă verificarea juridică sau corectitudinea licenței.
6. T6 demonstrează limita semnării: modificarea făcută înainte de semnarea legitimă este acceptată. Nu reproduce compromiterea SolarWinds.
7. Secțiunea 5.5 descrie recomandări pentru CI, OCI și atestări. Experimentul E2 cu fișiere și chei locale nu verifică OIDC, atestări OCI, SLSA sau politici Kubernetes. Acestea nu sunt declarate implementate prin simpla reușită a T0–T6.
8. La repetarea experimentului, lockfile-ul arhivat trebuie păstrat. Recalcularea lui în alt moment poate schimba referința și rezultatele.

## Rulare și consultare

Prima rulare necesită acces la rețea, Python 3.11+, npm și Cosign în `.venv/bin/cosign`:

```bash
python3 -m supplyguard experiment --prepare
```

Pentru repetare cu sursele și uneltele deja descărcate:

```bash
python3 -m supplyguard experiment
```

Repetarea poate accesa registrele npm/PyPI și URL-ul arhivei accepts. Scripturile npm sunt dezactivate prin `--ignore-scripts`; pachetele Python se instalează numai din wheel-uri.

Pentru regenerarea raportului din măsurătorile salvate, fără scanări sau instalări:

```bash
python3 scripts/reproduce_chapters.py --report-only
```

În GUI, operațiunea „Experimente capitolele 4 și 5” rulează evaluarea, iar butonul „Tabele E1/E2” deschide rezultatele existente. Cheile experimentale rămân în directorul local ignorat de Git `build/experiments/sigstore/`; nu sunt chei de release.
