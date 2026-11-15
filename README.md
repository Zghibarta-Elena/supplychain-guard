# SupplyGuard

[Prezentarea software-ului cu 11 capturi reale de ecran](docs/prezentare-software-cu-capturi.md) explică intrările, operațiunile, rezultatele și limitele fiecărei funcții.

Experimentele reale din capitolele 4 și 5: [analiză și instrucțiuni](docs/analiza-capitole-4-5.md), [rezultate Express, Flask și Cosign](docs/experimente-capitole-4-5.md). Rulare inițială: `python3 -m supplyguard experiment --prepare` (Python 3.11+, npm și Cosign necesare).

Framework practic pentru protecția lanțului de aprovizionare software în organizații mici. Include inventariere SHA-256, generare SBOM cu Syft, politici pentru componente, semnare și verificare Sigstore/Cosign și laboratoare inofensive inspirate de SolarWinds și XZ Utils.

Necesită Python 3.10+. Comenzile locale nu necesită biblioteci suplimentare. Syft și Cosign trebuie instalate separat pentru generare SBOM și semnare; nu sunt descărcate sau executate automat de la distanță.

```bash
python3 -m supplyguard --help
python3 -m unittest discover -s tests -v
python3 -m supplyguard check examples/clean.cdx.json
python3 -m supplyguard check examples/blocked.cdx.json  # exit 1: blocat
python3 -m supplyguard simulate solarwinds
python3 -m supplyguard simulate xz
```

## Flux de release

1. Revizuiți codul și dependențele; folosiți un runner izolat și dependențe fixate.
2. Construiți artefactul într-un director `release/`. Salvați inventarul aprobat în afara acestuia, pe un canal protejat:

```bash
python3 -m supplyguard snapshot release --output release-baseline.json
python3 -m supplyguard compare release --baseline release-baseline.json
python3 -m supplyguard sbom dir:release --output release.cdx.json
python3 -m supplyguard check release.cdx.json --policy policy.json
```

3. Semnați separat artefactul final și SBOM-ul. Exemplu pentru un artefact creat de procesul vostru de build:

```bash
python3 -m supplyguard sign release/application.tar.gz --bundle application.sigstore.json
python3 -m supplyguard sign release.cdx.json --bundle sbom.sigstore.json
```

Cosign keyless poate deschide autentificarea OIDC și folosește servicii externe Sigstore. `--yes` acceptă publicarea datelor de semnare în jurnalul de transparență; evitați metadate confidențiale. Nu utilizați identitatea exemplu de mai jos în producție.

4. La recepție, verificați ambele fișiere cu identitatea exactă și issuer-ul aprobate, apoi evaluați SBOM-ul:

```bash
python3 -m supplyguard verify release/application.tar.gz --bundle application.sigstore.json --identity 'release@example.org' --issuer 'https://accounts.google.com'
python3 -m supplyguard verify release.cdx.json --bundle sbom.sigstore.json --identity 'release@example.org' --issuer 'https://accounts.google.com'
python3 -m supplyguard check release.cdx.json
```

Pentru GitHub Actions folosiți identitatea exactă a workflow-ului de release și issuer `https://token.actions.githubusercontent.com`. Semnarea necesită `id-token: write` doar în jobul de release protejat. Workflow-ul inclus rulează verificările locale; nu publică release-uri și nu semnează.

## Limite și interpretare

Coduri de ieșire: `0` succes, `1` politică încălcată/modificări detectate, `2` eroare de input sau unealtă. Simulările returnează succes când demonstrația rulează, iar rezultatul conține `detected`.

Inventarul detectează diferențe față de o bază de încredere; o bază creată după compromitere nu dovedește integritatea. SBOM-ul este un inventar, nu dovada absenței codului malițios. Verificarea politicii nu validează schema CycloneDX completă și nu este un scanner CVE. Regulile XZ sunt exemple cu potrivire exactă, nu acoperă toate denumirile/pachetele distribuțiilor sau versiunile cu sufixe. Adaptați politica și folosiți suplimentar un scanner de vulnerabilități cu bază actualizată.

O semnătură validă confirmă identitatea semnatarului și integritatea fișierului, nu siguranța codului sau a build-ului. Semnarea separată a SBOM-ului nu demonstrează că descrie acel artefact: păstrați asocierea printr-un manifest de release semnat sau o atestare de proveniență verificată. Acest prototip nu implementează verificarea provenienței SLSA, reproducibilitate automată sau sandbox pentru build-uri nefiabile.

Consultați [analiza incidentelor](docs/incidents.md) și [planul operațional](docs/operations.md).

## Instalarea locală disponibilă

În acest workspace, SupplyGuard, Syft 1.57.0 și Cosign 3.1.4 sunt instalate în `.venv/bin`. Activați mediul din rădăcina proiectului:

```bash
source .venv/bin/activate
supplyguard --help
syft version
cosign version
```

Mediul virtual este local și ignorat de Git. Pentru reinstalarea pachetului Python: `python3 -m venv .venv` și `.venv/bin/python -m pip install -e .`. Instalați separat binarele oficiale Syft/Cosign și verificați digesturile lor înainte de execuție.

Ghid pas cu pas: [instalare și utilizare pe Linux și Windows](docs/ghid-utilizare.md).

## Interfață grafică desktop

După instalarea/actualizarea pachetului în mediul virtual:

```bash
.venv/bin/python -m pip install -e .
.venv/bin/supplyguard-gui
```

Pe Ubuntu/Debian, interfața necesită Tkinter: `sudo apt install python3-tk`.
Pe Windows, instalați Python cu opțiunea Tcl/Tk, apoi rulați:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\supplyguard-gui.exe
```

Selectați operațiunea, alegeți fișierele/directoarele și apăsați „Rulează operațiunea”. Rezultatele apar în fila „Tabel”, cu indicatorul și valoarea pe coloane, și pot fi exportate în CSV. Fila „Jurnal” păstrează ieșirea completă și permite exportul în TXT. Operațiunile rulează în fundal; așteptați finalizarea înainte de închiderea ferestrei. Pentru semnarea keyless, autentificarea Cosign se face în browser. Syft și Cosign trebuie instalate pentru operațiunile care le folosesc; GUI-ul caută și în directorul executabilului Python din mediul virtual.

## Exemple rulate

Rezultatele pentru SBOM acceptat, SBOM blocat și simulările SolarWinds/XZ sunt disponibile în [tabelul CSV](examples/results.csv). Simulările folosesc numai fișiere text temporare. Pentru repetare, rulați comenzile din primul bloc al acestui ghid.
