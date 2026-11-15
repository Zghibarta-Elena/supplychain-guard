# SupplyGuard — descrierea software-ului și rezultatele evaluării

Acest document descrie evaluarea demonstrativă inițială. Pentru experimentele reale Express/Flask și scenariile criptografice din capitolele 4 și 5, consultați [raportul experimental ulterior](experimente-capitole-4-5.md) și [analiza cerințelor](analiza-capitole-4-5.md).

## 4.1 Scopul software-ului

SupplyGuard 0.1.0 este un framework Python pentru verificarea integrității fișierelor și controlul componentelor software înainte de livrarea unei aplicații. Reunește inventarierea SHA-256, evaluarea unui SBOM pe baza unei politici locale și integrarea cu Syft și Cosign. Poate fi utilizat din linia de comandă sau dintr-o interfață desktop Tkinter.

Un SBOM (Software Bill of Materials) este inventarul componentelor unei aplicații. SupplyGuard verifică inventare în format CycloneDX JSON: controlează existența numelui, versiunii și, conform politicii, a identificatorului purl și semnalează combinațiile nume–versiune interzise. Politica inclusă conține reguli pentru versiunile 5.6.0 și 5.6.1 ale componentelor denumite exact `xz`, `xz-utils` și `liblzma`.

Separat, software-ul poate salva hash-ul SHA-256 al fiecărui fișier dintr-un director și poate compara ulterior directorul cu inventarul aprobat. Comparația identifică fișiere adăugate, eliminate și modificate. Această verificare presupune că inventarul inițial provine dintr-o stare de încredere.

| Funcție | Comandă | Rol și rezultat |
|---|---|---|
| Inventariere | `snapshot` | Salvează căile relative și hash-urile SHA-256 într-un fișier JSON, în afara directorului scanat. |
| Verificarea integrității | `compare` | Compară directorul cu inventarul aprobat și raportează diferențele. |
| Generare SBOM | `sbom` | Apelează Syft instalat separat pentru generarea unui inventar CycloneDX. |
| Evaluare SBOM | `check` | Aplică politica JSON și raportează încălcările. |
| Semnare | `sign` | Apelează Cosign pentru semnarea unui artefact și salvarea unui bundle Sigstore. |
| Verificarea semnăturii | `verify` | Apelează Cosign cu identitatea și issuer-ul OIDC aprobate. |
| Laborator | `simulate` | Demonstrează detectarea unei modificări sau adăugări de fișier, folosind fișiere text temporare. |
| Afișare și export | Interfața desktop | Prezintă rezultatele în tabel, permite export CSV și păstrează jurnalul cu export TXT. |

## 4.2 Metoda de evaluare

Evaluarea locală a fost executată la 12 noiembrie 2026, utilizând comenzile reale ale framework-ului și suita de teste `unittest`. Verificările SBOM au folosit fișierele demonstrative din `examples/` și politica `policy.json`. Verificările de integritate au folosit un director temporar cu două fișiere inițiale.

Rezultatele de mai jos reprezintă verificări funcționale pe exemple controlate. Nu reprezintă un benchmark pe proiectele Express sau Flask. Valorile din modelul de prezentare furnizat pentru aceste proiecte nu au fost măsurate în această evaluare și nu sunt atribuite SupplyGuard.

Codul de ieșire `0` indică finalizarea cu succes, `1` indică încălcări ale politicii sau diferențe de integritate, iar `2` indică o eroare de intrare ori de execuție. La simulări, detectarea este raportată prin câmpul `detected`; codul `0` indică executarea demonstrației.

## 4.3 Rezultate

**Tabelul 4.1 – Evaluarea SBOM-urilor demonstrative, referință: câte o componentă CycloneDX în fiecare fișier**

| Cfg. | Momentul evaluării / intrare | Politică | Componente evaluate | Încălcări raportate | Rezultat | Cod de ieșire |
|---|---|---|---:|---:|---|---:|
| A | SBOM existent: `examples/clean.cdx.json` | `policy.json` | 1: `demo@1.0.0` | 0 | Acceptat: `passed=true` | 0 |
| B | SBOM existent: `examples/blocked.cdx.json` | `policy.json` | 1: `xz@5.6.1` | 1 | Respins de regula pentru componenta interzisă: `passed=false` | 1 |

În configurațiile A și B, Syft nu a fost apelat: fișierele CycloneDX existau deja. Acoperirea față de un lockfile, procentul de componente cu hash și procentul cu licență nu au fost măsurate. Numărul de componente din aceste exemple nu permite deducerea acoperirii unei aplicații reale.

**Tabelul 4.2 – Verificarea integrității, referință: inventar SHA-256 aprobat pentru două fișiere**

| Cfg. | Momentul verificării | Fișiere inițiale | Fișiere adăugate | Fișiere eliminate | Fișiere modificate | Rezultat | Cod de ieșire |
|---|---|---:|---|---|---|---|---:|
| C | Crearea inventarului prin `snapshot` | 2 | – | – | – | Inventar JSON creat | 0 |
| D | Comparare imediat după inventariere | 2 | 0 | 0 | 0 | Fără diferențe | 0 |
| E | Comparare după trei intervenții controlate | 2 | 1: `new.txt` | 1: `obsolete.txt` | 1: `application.txt` | Toate cele trei intervenții raportate | 1 |

În configurația E, conținutul `application.txt` a fost schimbat, `obsolete.txt` a fost șters și `new.txt` a fost creat după salvarea inventarului. Toate cele trei intervenții introduse au fost detectate; acest rezultat nu constituie o rată generală de detecție a atacurilor.

**Tabelul 4.3 – Laboratoare demonstrative, referință: un fișier text aprobat înainte de intervenție**

| Cfg. | Scenariu | Intervenție simulată | Fișiere adăugate | Fișiere modificate | Detectare (`detected`) | Cod de ieșire |
|---|---|---|---|---|---|---:|
| F | SolarWinds | Adăugare de text în fișierul aplicației | 0 | 1: `application.txt` | Da | 0 |
| G | XZ | Introducerea unui fișier suplimentar în director | 1: `release-only.m4` | 0 | Da | 0 |

Laboratoarele ilustrează tipare de modificare a fișierelor. Nu execută malware și nu reproduc exploatarea istorică a incidentelor ale căror nume sunt folosite.

**Tabelul 4.4 – Verificări automate, referință: 13 teste executate prin `unittest`**

| Grup | Teste executate | Teste trecute | Ce verifică |
|---|---:|---:|---|
| Funcționalități framework | 7 | 7 | Simulări, diferențe de inventar, politică și componente imbricate, intrări invalide, respingerea legăturilor simbolice, coduri de ieșire și argumentele verificării Cosign. |
| Construirea comenzilor GUI | 4 | 4 | Scenariu selectat, câmpuri obligatorii, căi cu spații și metacaractere, fișiere inexistente. |
| Conversia rezultatelor în tabel | 2 | 2 | Păstrarea constatărilor imbricate și a mesajelor de eroare. |
| **Total** | **13** | **13** | **Suita a trecut integral.** |

Testul Cosign utilizează un apel simulat pentru a verifica transmiterea identității și issuer-ului. Nu reprezintă o semnare sau verificare criptografică reală. Interfața desktop nu a fost verificată vizual în această evaluare.

## 4.4 Interpretarea rezultatelor

**R1. Politica distinge între componenta permisă și componenta interzisă.** Configurația A a fost acceptată, iar configurația B a produs o constatare pentru `xz@5.6.1`. Rezultatul confirmă aplicarea regulii locale pe exemplul verificat. Framework-ul nu consultă automat o bază de vulnerabilități și nu validează integral schema CycloneDX.

**R2. Inventarul detectează cele trei categorii de diferențe.** Configurația D nu a raportat modificări, iar configurația E a identificat exact fișierul adăugat, fișierul eliminat și fișierul modificat. Credibilitatea rezultatului depinde de protejarea inventarului aprobat: un inventar creat după compromitere poate considera fișierele compromise drept referință.

**R3. Hash-urile fișierelor și hash-urile componentelor SBOM au roluri diferite.** Comanda `snapshot` calculează SHA-256 pentru fișierele locale. Aceasta nu completează automat hash-uri în componentele CycloneDX. În evaluarea prezentă nu s-a implementat și nu s-a verificat completarea hash-urilor dintr-un lockfile.

**R4. Simulările confirmă comportamentul demonstrațiilor.** Ambele scenarii au raportat `detected=true`, pentru intervențiile controlate introduse de cod. Rezultatul nu demonstrează detectarea completă a unui atac SolarWinds sau XZ real și nu măsoară eficiența față de atacuri necunoscute.

**R5. Tabelul face rezultatele mai ușor de consultat.** Interfața transformă rezultatele JSON în perechi indicator–valoare, inclusiv listele de constatări și diferențele imbricate. Exportul CSV permite prelucrarea ulterioară. Jurnalul păstrează mesajele complete ale comenzilor.

**R6. Acoperirea inventarului de dependențe rămâne de evaluat.** Exemplele executate nu compară SBOM-ul cu un lockfile și nu măsoară efectul versiunii Syft, al dependențelor de dezvoltare sau al domeniului scanării. Pentru concluzii de tipul celor din tabelele Express/Flask este necesar un experiment separat, cu proiecte și versiuni fixate, număr de referință al pachetelor și configurații documentate.

## 4.5 Contribuție practică: verificare unificată și raportare tabelară

Contribuția practică a prototipului constă în reunirea verificărilor locale de integritate și politică într-un flux accesibil din CLI și GUI. Rezultatele structurale sunt prezentate într-un tabel și pot fi exportate CSV, iar codurile de ieșire permit folosirea verificărilor în automatizări CI.

Fișierul [results.csv](../examples/results.csv) păstrează rezultatele celor patru exemple SBOM și laborator. Configurațiile C–E din acest document au fost executate suplimentar într-un director temporar, eliminat automat la final.

Generarea SBOM prin Syft, semnarea și verificarea reală prin Cosign sunt integrări disponibile în cod, dar nu au fost executate în evaluarea descrisă aici. Prototipul nu implementează verificarea provenienței SLSA, reproducibilitatea automată a build-urilor sau izolarea build-urilor nefiabile.

## 4.6 Recomandări derivate

1. Inventarul aprobat se creează dintr-o stare verificată și se păstrează separat, pe un canal protejat. Rezultatul configurației E este util numai în raport cu o astfel de referință.
2. Politica de componente se adaptează aplicației și se actualizează. Verificarea locală se completează cu un scanner de vulnerabilități cu bază actualizată.
3. SBOM-ul se generează după rezolvarea dependențelor, iar versiunea Syft și opțiunile de scanare se înregistrează pentru fiecare experiment. Această recomandare urmează să fie evaluată prin măsurători de acoperire pe proiecte reale.
4. Pentru o evaluare extinsă se raportează separat componentele de rulare și cele de dezvoltare, acoperirea față de lockfile, componentele străine, hash-urile și licențele. Valorile nemăsurate se marchează explicit.
5. În CI, codurile de ieșire `1` și `2` se tratează ca motive de oprire și analiză. Acceptarea unei componente prin politica locală nu reprezintă o garanție a siguranței sale.
6. Artefactul și SBOM-ul se semnează și se verifică folosind identitatea și issuer-ul aprobate. Asocierea dintre ele se păstrează printr-un manifest semnat sau o atestare de proveniență verificată.

## Anexă — repetarea verificărilor de bază

Comenzile se execută din rădăcina proiectului:

```bash
python3 -m supplyguard check examples/clean.cdx.json
python3 -m supplyguard check examples/blocked.cdx.json
python3 -m supplyguard simulate solarwinds
python3 -m supplyguard simulate xz
python3 -m unittest discover -s tests -v
```

Comanda pentru SBOM-ul blocat returnează intenționat codul `1`. Cele două simulări returnează `0` atunci când demonstrația rulează cu succes; detectarea intervenției se citește din câmpul `detected`.
