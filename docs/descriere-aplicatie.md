# SupplyGuard — descrierea exactă a aplicației

SupplyGuard este o aplicație desktop și un instrument de linie de comandă pentru verificarea componentelor, integrității fișierelor și semnăturilor unei livrări software. Include și un flux experimental pentru evaluarea SBOM-urilor proiectelor Express și Flask și pentru testarea semnăturilor cu Cosign.

Utilizatorul selectează operațiunea, alege fișierele sau directoarele necesare și pornește execuția. Interfața afișează rezultatele într-un tabel și păstrează mesajele complete în fila „Jurnal”.

## Funcțiile aplicației

| Funcție | Ce face exact | Rezultatul obținut |
|---|---|---|
| Generare SBOM | Apelează Syft pentru identificarea componentelor software dintr-un director. | Un inventar CycloneDX JSON cu componentele identificate de Syft. |
| Verificare SBOM | Verifică existența numelui și versiunii componentelor, inclusiv a celor imbricate, precum și existența identificatorului purl dacă politica îl cere. Compară componentele cu regulile locale de interzicere nume–versiune. | Acceptare sau o listă de încălcări. Politica inclusă respinge, de exemplu, `xz@5.6.1`. |
| Inventar aprobat | Calculează hash-ul SHA-256 al fiecărui fișier dintr-un director și îl asociază cu respectiva cale relativă. Respinge legăturile simbolice și cere salvarea inventarului în afara directorului scanat. | Un fișier JSON folosit drept referință pentru comparații ulterioare. |
| Comparare integritate | Recalculează inventarul directorului și compară căile și hash-urile cu referința aprobată. | Listele fișierelor adăugate, eliminate și modificate. |
| Semnare artefact | Apelează Cosign `sign-blob` pentru semnarea unui fișier. Fluxul standard folosește semnare keyless, cu autentificare OIDC și servicii Sigstore. | Un bundle Sigstore asociat fișierului semnat. |
| Verificare semnătură | Apelează Cosign `verify-blob` pentru verificarea fișierului și a bundle-ului, folosind identitatea și emitentul OIDC aprobate de utilizator. | Confirmarea verificării sau o eroare. |
| Laborator SolarWinds | Creează un fișier text temporar, salvează inventarul și apoi modifică fișierul prin adăugarea unui marker inofensiv. | Raportarea fișierului modificat și a câmpului `detected`. |
| Laborator XZ | Creează un inventar temporar și apoi adaugă un fișier text suplimentar. | Raportarea fișierului adăugat și a câmpului `detected`. |
| Experimente Express/Flask | Generează SBOM-uri cu Syft 1.18.1 și 1.56.0, înainte și după instalarea dependențelor, cu configurații distincte. Compară rezultatele cu referințele de dependențe. | Tabele cu numărul componentelor, acoperirea, componentele suplimentare și procentele cu PURL, hash și licență. |
| Completare hash-uri | Citește câmpul `integrity` în format SRI din `package-lock.json`, decodează digesturile și le adaugă componentelor npm CycloneDX cu aceeași pereche nume–versiune. Păstrează hash-urile existente și nu alege arbitrar între integrități conflictuale. | SBOM-uri completate cu hash-urile arhivelor pachetelor npm. |
| Experimente Cosign T0–T6 | Semnează și verifică artefacte originale sau modificate folosind două perechi de chei locale: legitimă și de atacator. Acest flux experimental nu folosește OIDC sau jurnal de transparență. | Rezultate de acceptare/respingere pentru șapte scenarii și durate pentru 20 de semnări și 20 de verificări. |
| Tabele E1/E2 | Încarcă măsurătorile salvate de experimente, fără să execute automat scanări noi. | Patru file tabelare: Express, Flask, hash-uri și Cosign. |
| Afișare și export | Afișează rezultatul operațiunii și jurnalul. Permite exportul tabelului principal în CSV și al jurnalului în TXT. Fluxul experimental generează separat rapoarte și CSV-uri. | Fișiere locale pentru consultare, analiză și documentare. |

Un SBOM (Software Bill of Materials) este un inventar al componentelor software. Identificatorul purl descrie un pachet într-un format standardizat. Hash-ul reprezintă un digest al conținutului, utilizat pentru comparații de integritate.

## Exemplu de utilizare

Înainte de livrarea unei aplicații, utilizatorul creează inventarul fișierelor aprobate și îl păstrează protejat. La o verificare ulterioară, SupplyGuard recalculează hash-urile și raportează dacă un fișier a fost modificat, șters sau adăugat.

Separat, utilizatorul poate genera un SBOM și îl poate verifica față de politica organizației. Dacă inventarul conține o combinație nume–versiune interzisă, aplicația raportează încălcarea. Artefactul poate fi semnat și verificat prin Cosign, folosind identitatea aprobată.

| Etapă | Acțiunea utilizatorului | Ce verifică aplicația |
|---|---|---|
| 1 | Selectează directorul aplicației și creează inventarul aprobat. | Calculează referința SHA-256 a fișierelor. |
| 2 | Compară ulterior directorul cu inventarul salvat. | Detectează diferențele față de referință. |
| 3 | Generează SBOM-ul prin Syft. | Inventariază componentele pe care Syft le identifică în domeniul scanat. |
| 4 | Verifică SBOM-ul cu politica locală. | Controlează câmpurile cerute și regulile de interzicere configurate. |
| 5 | Semnează și verifică artefactul cu Cosign. | Verifică integritatea față de semnătură și semnatarul aprobat. |
| 6 | Exportă rezultatele. | Salvează constatările pentru analiză sau documentare. |

## Semnificația rezultatelor

| Cod de ieșire | Semnificație |
|---|---|
| `0` | Operațiunea s-a încheiat cu succes. La simulări, detectarea intervenției este raportată separat prin `detected`. |
| `1` | Verificarea politicii a găsit încălcări sau comparația de integritate a detectat diferențe. |
| `2` | A apărut o eroare de intrare sau de execuție a unei unelte. |

## Rolul componentelor tehnice

| Componentă | Responsabilitate |
|---|---|
| SupplyGuard | Coordonează operațiunile, calculează inventarele locale, aplică politica, calculează metricile experimentale și prezintă rezultatele. |
| Syft | Identifică și inventariază componentele software pentru generarea SBOM-urilor. |
| Cosign | Execută semnarea și verificarea criptografică. |
| Tkinter | Furnizează interfața desktop. |
| `policy.json` | Definește regulile locale pentru verificarea componentelor. |

## Limitele aplicației

SupplyGuard verifică proprietățile descrise mai sus. Nu este un scanner CVE cu bază de vulnerabilități actualizată și nu identifică automat orice malware. Verificarea SBOM nu validează integral schema CycloneDX și nu garantează că inventarul descrie complet aplicația.

Comparația de integritate depinde de o referință de încredere. Dacă inventarul este creat după compromitere sau poate fi înlocuit de atacator, comparația nu mai oferă aceeași garanție.

O semnătură validă confirmă integritatea față de momentul semnării și semnatarul verificat. Nu garantează siguranța conținutului: un artefact compromis înainte de semnarea legitimă poate trece verificarea. Semnarea separată a unui artefact și a unui SBOM nu demonstrează automat asocierea dintre ele.

Laboratoarele SolarWinds și XZ folosesc fișiere text inofensive. Ele ilustrează detectarea diferențelor de inventar și nu reproduc atacurile istorice.

Prototipul nu implementează verificarea provenienței SLSA, build reproductibil automat sau politici de admitere Kubernetes. Codurile de ieșire pot fi folosite în automatizări, dar oprirea efectivă a unui release sau deployment necesită configurarea pipeline-ului care apelează aplicația.

## Documente asociate

- [Prezentarea cu 11 capturi reale de ecran](prezentare-software-cu-capturi.md)
- [Rezultatele experimentale Express, Flask și Cosign](experimente-capitole-4-5.md)
- [Analiza cerințelor din capitolele 4 și 5](analiza-capitole-4-5.md)
