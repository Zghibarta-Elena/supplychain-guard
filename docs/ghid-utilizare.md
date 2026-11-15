# Ghid de instalare și utilizare SupplyGuard

Acest ghid explică instalarea pe Linux și Windows, testarea funcțiilor și utilizarea pe o aplicație reală.

SupplyGuard este un prototip CLI: rulează la cerere din terminal și nu monitorizează automat calculatorul. Verifică integritatea fișierelor, generează inventare de componente software (SBOM), aplică politici locale și integrează semnarea/verificarea cu Sigstore Cosign.

## 1. Ce face fiecare comandă

| Comandă | Rol |
| --- | --- |
| `snapshot` | Salvează hash-urile SHA-256 ale fișierelor dintr-un director aprobat. |
| `compare` | Detectează fișiere adăugate, șterse sau modificate față de inventarul salvat. |
| `sbom` | Folosește Syft pentru a genera un SBOM în format CycloneDX JSON. |
| `check` | Verifică componentele SBOM-ului conform regulilor din `policy.json`. |
| `sign` | Semnează un fișier folosind Cosign și identitatea semnatarului. |
| `verify` | Verifică semnătura, identitatea exactă și furnizorul de identitate așteptat. |
| `simulate` | Rulează demonstrații inofensive inspirate de SolarWinds și XZ Utils. |

Cerințe: Python 3.10 sau mai nou. Syft este necesar pentru `sbom`; Cosign este necesar pentru `sign` și `verify`. Celelalte comenzi nu necesită aceste două unelte.

## 2. Instalarea pe Linux

### 2.1. Instalarea SupplyGuard

Deschide terminalul în directorul proiectului:

```bash
cd ~/GolandProjects/supplychain_framework
python3 -m venv .venv
.venv/bin/python -m pip install -e .
source .venv/bin/activate
supplyguard --help
```

În workspace-ul în care a fost creat proiectul, instalarea este deja făcută. Pentru o sesiune nouă sunt suficiente:

```bash
cd ~/GolandProjects/supplychain_framework
source .venv/bin/activate
```

### 2.2. Instalarea Syft și Cosign

În workspace-ul inițial sunt instalate Syft 1.57.0 și Cosign 3.1.4 în `.venv/bin`. Verifică:

```bash
syft version
cosign version
```

Pe alt calculator Linux:

1. Descarcă arhiva Syft și executabilul Cosign pentru sistemul și arhitectura calculatorului din release-urile oficiale de mai jos.
2. Compară SHA-256 cu digestul/checksum-ul oficial al fișierului descărcat:

   ```bash
   sha256sum /cale/catre/arhiva-syft.tar.gz
   sha256sum /cale/catre/cosign-linux-amd64
   ```

3. Extrage executabilul `syft` din arhivă și copiază-l în `.venv/bin/syft`.
4. Copiază executabilul Cosign în `.venv/bin/cosign`.
5. Acordă drept de execuție:

   ```bash
   chmod +x .venv/bin/syft .venv/bin/cosign
   ```

6. Activează mediul și verifică versiunile.

Surse oficiale:

- [Instalare Syft](https://oss.anchore.com/docs/installation/syft/)
- [Release-uri Syft](https://github.com/anchore/syft/releases)
- [Instalare Cosign](https://docs.sigstore.dev/cosign/system_config/installation/)
- [Release-uri Cosign](https://github.com/sigstore/cosign/releases)

## 3. Instalarea pe Windows

Pașii de mai jos sunt pentru PowerShell. Proiectul folosește Python și căi portabile, dar rularea pe Windows nu a fost încă validată în acest workspace.

### 3.1. Copierea proiectului și instalarea Python

1. Instalează Python 3.10 sau mai nou de pe [python.org](https://www.python.org/downloads/windows/).
2. Copiază sursele proiectului, de exemplu în `C:\Projects\supplychain_framework`.
3. Nu copia mediul `.venv` de pe Linux: mediile virtuale trebuie recreate pe fiecare sistem.

### 3.2. Instalarea SupplyGuard în PowerShell

```powershell
cd C:\Projects\supplychain_framework
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\supplyguard.exe --help
```

Comenzile din acest ghid folosesc executabilul direct, fără activarea mediului. Opțional, poți activa mediul:

```powershell
.\.venv\Scripts\Activate.ps1
supplyguard --help
```

Dacă politica PowerShell blochează activarea, poți continua cu executabilul direct; activarea nu este obligatorie.

### 3.3. Instalarea Syft

Dacă ai WinGet:

```powershell
winget install --id Anchore.Syft --exact
```

Redeschide PowerShell și verifică:

```powershell
syft version
```

Alternativ, descarcă arhiva Windows pentru arhitectura ta din [release-urile oficiale Syft](https://github.com/anchore/syft/releases), verifică checksum-ul, extrage `syft.exe` și copiază-l în `.venv\Scripts`.

### 3.4. Instalarea Cosign

1. Descarcă executabilul Windows pentru arhitectura ta din [release-urile oficiale Cosign](https://github.com/sigstore/cosign/releases). Pentru Windows x64, numele este de forma `cosign-windows-amd64.exe`.
2. Verifică SHA-256 față de digestul/checksum-ul oficial:

   ```powershell
   Get-FileHash "$env:USERPROFILE\Downloads\cosign-windows-amd64.exe" -Algorithm SHA256
   ```

3. Copiază-l în directorul proiectului, în `.venv\Scripts`, cu numele `cosign.exe`.
4. Verifică:

   ```powershell
   .\.venv\Scripts\cosign.exe version
   ```

SupplyGuard caută `syft` și `cosign` în `PATH`. Dacă ai copiat executabilele în `.venv\Scripts` și nu ai activat mediul, adaugă directorul în `PATH` pentru sesiunea curentă:

```powershell
cd C:\Projects\supplychain_framework
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
```

## 4. Testarea instalării

Rulează comenzile din directorul SupplyGuard, deoarece exemplele și politica sunt căi relative.

### Linux, cu mediul activat

```bash
supplyguard simulate solarwinds
supplyguard simulate xz
supplyguard check examples/clean.cdx.json
supplyguard check examples/blocked.cdx.json
python -m unittest discover -s tests -v
```

### Windows, în PowerShell

```powershell
.\.venv\Scripts\supplyguard.exe simulate solarwinds
.\.venv\Scripts\supplyguard.exe simulate xz
.\.venv\Scripts\supplyguard.exe check examples\clean.cdx.json
.\.venv\Scripts\supplyguard.exe check examples\blocked.cdx.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Rezultatele așteptate

- SolarWinds: `detected: true`, cu `application.txt` în lista `changed`.
- XZ: `detected: true`, cu `release-only.m4` în lista `added`.
- SBOM curat: `passed: true`.
- SBOM blocat: `passed: false`, deoarece include XZ 5.6.1.

Simulările creează numai fișiere text temporare. Nu execută malware și nu reproduc tehnic exploatarea istorică a incidentelor.

## 5. Utilizarea reală pe Linux: exemplu Go

Înlocuiește `~/proiecte/aplicatia-mea` cu directorul aplicației tale Go. Acest exemplu presupune că pachetul principal se află în rădăcina proiectului.

### 5.1. Construiește aplicația

```bash
source ~/GolandProjects/supplychain_framework/.venv/bin/activate
cd ~/proiecte/aplicatia-mea
mkdir -p release
go build -o release/aplicatie .
```

Pune în `release/` numai fișierele care trebuie livrate.

### 5.2. Generează SBOM-ul și verifică politica

```bash
supplyguard sbom dir:release --output aplicatie.cdx.json
supplyguard check aplicatie.cdx.json --policy ~/GolandProjects/supplychain_framework/policy.json
```

Calitatea inventarului depinde de ce identifică Syft în aplicație. Dacă verificarea eșuează, investighează constatările. Nu elimina automat reguli doar pentru a obține un rezultat pozitiv.

### 5.3. Salvează inventarul aprobat

După revizuirea aplicației și aprobarea build-ului:

```bash
supplyguard snapshot release --output baseline.json
```

Inventarul trebuie salvat în afara directorului scanat. Păstrează o copie protejată de modificări neautorizate. O bază creată după compromitere nu demonstrează că fișierele sunt sigure.

### 5.4. Verifică înainte de livrare

```bash
supplyguard compare release --baseline baseline.json
```

Dacă nu sunt modificări, rezultatul este:

```json
{
  "added": [],
  "removed": [],
  "changed": []
}
```

Orice diferență trebuie explicată și aprobată. Un build nou poate produce diferențe legitime; verifică noua versiune înainte de a crea un inventar nou.

### 5.5. Semnează executabilul și SBOM-ul

```bash
supplyguard sign release/aplicatie --bundle aplicatie.sigstore.json
supplyguard sign aplicatie.cdx.json --bundle sbom.sigstore.json
```

Cosign poate deschide browserul pentru autentificare OIDC. Integrarea folosește servicii externe Sigstore. Comanda `sign` transmite `--yes` către Cosign, acceptând publicarea datelor de semnare în jurnalul de transparență; nu include metadate confidențiale.

Livrează executabilul, SBOM-ul și cele două bundle-uri. Pentru a demonstra asocierea SBOM-ului cu executabilul este necesar suplimentar un manifest semnat sau o atestare verificabilă; prototipul nu automatizează această asociere.

### 5.6. Verificarea de către destinatar

Exemplu pentru un semnatar autentificat prin Google; înlocuiește adresa cu identitatea exactă aprobată:

```bash
supplyguard verify release/aplicatie --bundle aplicatie.sigstore.json --identity 'adresa-ta@gmail.com' --issuer 'https://accounts.google.com'
supplyguard verify aplicatie.cdx.json --bundle sbom.sigstore.json --identity 'adresa-ta@gmail.com' --issuer 'https://accounts.google.com'
supplyguard check aplicatie.cdx.json --policy ~/GolandProjects/supplychain_framework/policy.json
```

Identitatea și issuer-ul trebuie cunoscute dintr-o sursă de încredere, nu preluate fără verificare din fișierele primite. Pentru semnături GitHub Actions se folosește identitatea exactă a workflow-ului aprobat și issuer-ul `https://token.actions.githubusercontent.com`.

## 6. Utilizarea reală pe Windows

Exemplul presupune că aplicația este deja construită, iar fișierele de livrat sunt în `C:\Livrari\AplicatiaMea`. Executabilul exemplu este `aplicatie.exe`.

### 6.1. Pregătește sesiunea PowerShell

```powershell
cd C:\Projects\supplychain_framework
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
supplyguard --help
syft version
cosign version
```

### 6.2. Generează și verifică SBOM-ul

```powershell
supplyguard sbom "dir:C:\Livrari\AplicatiaMea" --output aplicatie.cdx.json
supplyguard check aplicatie.cdx.json --policy policy.json
```

### 6.3. Salvează inventarul după aprobare

```powershell
supplyguard snapshot "C:\Livrari\AplicatiaMea" --output baseline.json
```

Fișierul `baseline.json` este creat în directorul SupplyGuard, separat de aplicația scanată. Păstrează-l protejat.

### 6.4. Verifică înainte de livrare

```powershell
supplyguard compare "C:\Livrari\AplicatiaMea" --baseline baseline.json
```

Listele `added`, `removed` și `changed` trebuie să fie goale pentru a confirma egalitatea cu inventarul aprobat.

### 6.5. Semnează executabilul și SBOM-ul

```powershell
supplyguard sign "C:\Livrari\AplicatiaMea\aplicatie.exe" --bundle aplicatie.sigstore.json
supplyguard sign aplicatie.cdx.json --bundle sbom.sigstore.json
```

Autentifică-te atunci când Cosign solicită acest lucru. Bundle-urile se creează în directorul curent.

### 6.6. Verifică semnăturile

Exemplu pentru Google; înlocuiește identitatea:

```powershell
supplyguard verify "C:\Livrari\AplicatiaMea\aplicatie.exe" --bundle aplicatie.sigstore.json --identity "adresa-ta@gmail.com" --issuer "https://accounts.google.com"
supplyguard verify aplicatie.cdx.json --bundle sbom.sigstore.json --identity "adresa-ta@gmail.com" --issuer "https://accounts.google.com"
supplyguard check aplicatie.cdx.json --policy policy.json
```

Destinatarul folosește propriile căi către fișierele primite și identitatea aprobată a semnatarului. Semnătura Cosign este separată de executabil; acest flux nu aplică o semnătură Windows Authenticode și nu elimină automat avertizările SmartScreen.

## 7. Cum interpretezi rezultatele

| Cod de ieșire | Semnificație |
| --- | --- |
| `0` | Comanda a reușit. Pentru `check`, politica a trecut; pentru `compare`, nu sunt diferențe. |
| `1` | `check` a găsit încălcări sau `compare` a detectat diferențe. |
| `2` | Eroare de fișier, format, argumente sau unealtă externă. |

Simulările returnează `0` când demonstrația rulează; verifică separat câmpul `detected`.

Linux: vezi codul imediat după comandă cu `echo $?`. PowerShell: folosește `$LASTEXITCODE`.

## 8. Erori frecvente

### Comanda `supplyguard` nu este găsită

Activează mediul sau folosește calea completă:

```bash
.venv/bin/supplyguard --help
```

Pe Windows:

```powershell
.\.venv\Scripts\supplyguard.exe --help
```

### `syft` sau `cosign` nu este găsit

Verifică instalarea și `PATH`. Pe Windows, dacă executabilele sunt în `.venv\Scripts`, adaugă directorul în `PATH` conform pașilor de mai sus. Instalarea SupplyGuard prin pip nu instalează automat aceste două unelte.

### Nu este găsit `policy.json`

Politica implicită este căutată în directorul curent. Rulează din directorul SupplyGuard sau transmite calea explicită prin `--policy`.

### SBOM-ul conține componente fără versiune sau PURL

Politica actuală poate respinge componentele care nu au nume, versiune sau Package URL, inclusiv unele intrări de tip fișier generate de Syft. Analizează SBOM-ul și adaptează politica/implementarea la tipurile de componente necesare organizației; o astfel de constatare nu înseamnă automat existența unei vulnerabilități.

### Verificarea semnăturii eșuează

Verifică dacă artefactul și bundle-ul corespund, dacă fișierul a fost modificat și dacă identitatea/issuer-ul sunt cele aprobate. Nu ocoli verificarea identității pentru a accepta fișierul.

## 9. Ce trebuie adăugat pentru utilizare operațională

- Adaptarea politicii la componentele reale ale organizației. Regulile XZ existente folosesc potrivire exactă și nu acoperă toate denumirile sau versiunile distribuțiilor.
- Un scanner de vulnerabilități cu bază actualizată. `check` nu caută automat toate CVE-urile și nu validează schema CycloneDX completă.
- Asocierea verificabilă dintre artefact, SBOM, commit și build, prin manifest semnat sau atestare de proveniență.
- Integrarea comenzilor în CI/CD, cu oprirea livrării la verificări eșuate. Workflow-ul inclus verifică prototipul; nu publică și nu semnează release-uri reale.
- Protecția branch-urilor, MFA, acces minim, revizuire independentă și medii de build izolate.
- Procedură de retragere a release-urilor compromise și reconstruire într-un mediu curat.

O semnătură validă dovedește identitatea semnatarului și integritatea fișierului semnat, nu absența codului malițios. SBOM-ul este un inventar, iar comparația SHA-256 dovedește doar egalitatea față de baza aleasă. SupplyGuard nu este antivirus.

## 10. Documentație suplimentară

- [Prezentarea proiectului](../README.md)
- [Analiza SolarWinds și XZ Utils](incidents.md)
- [Plan operațional pentru organizații mici](operations.md)
- [Semnare blob cu Cosign](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/)
- [Verificare cu Cosign](https://docs.sigstore.dev/cosign/verifying/verify/)

## 11. Interfața grafică

GUI-ul desktop oferă aceleași operațiuni prin formulare în română și selectoare de fișiere/directoare.

Linux:

```bash
cd ~/GolandProjects/supplychain_framework
# Necesar o singură dată pe Ubuntu/Debian:
sudo apt install python3-tk
.venv/bin/python -m pip install -e .
.venv/bin/supplyguard-gui
```

Windows (Python trebuie instalat cu Tcl/Tk):

```powershell
cd C:\Projects\supplychain_framework
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\supplyguard-gui.exe
```

1. Alege operațiunea din lista de sus.
2. Selectează fișierele și directoarele. Pentru verificarea SBOM, politica proiectului este completată implicit.
3. Pentru verificarea unei semnături, introdu identitatea exactă și issuer-ul aprobate.
4. Apasă „Rulează operațiunea”. Bara de progres arată că operațiunea rulează, iar jurnalul afișează rezultatul.
5. „Constatări” înseamnă că politica sau comparația necesită analiză; nu înseamnă automat malware.
6. Folosește „Exportă rezultatul” pentru a salva jurnalul într-un fișier text.

La semnare, Cosign poate deschide browserul pentru autentificare. Așteaptă finalizarea operațiunii înainte de a închide aplicația. Nu este implementată anularea operațiunilor în curs.
