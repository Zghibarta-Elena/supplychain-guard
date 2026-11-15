# Rezultate experimentale — capitolele 4 și 5

Acest raport este generat din rulări reale prin `python3 scripts/reproduce_chapters.py`.
Data rulării: 2026-11-12 17:54:22 +0200. Metadatele și măsurătorile brute sunt în `build/experiments/measurements.json`, iar comenzile și ieșirile în `build/experiments/commands.log`.

## Metodă și diferențe față de documentul Word

Proiecte: Express v5.1.0 și Flask 3.1.1, arhive oficiale GitHub. Syft: 1.18.1 și 1.56.0, arhive verificate SHA-256 față de checksum-urile publicate. Instalarea npm folosește `--ignore-scripts`; mediul Flask folosește numai wheel-uri și șapte versiuni fixate. Cheile Cosign sunt locale, temporare pentru experiment, fără OIDC și fără jurnal public.

Mediul efectiv și versiunile sunt în tabelul următor. Lockfile-ul Express este generat la prima rulare și păstrat pentru repetări. Rezolvarea dependențelor la o altă dată poate modifica referința față de lucrare. Numărul componentelor este numărul intrărilor CycloneDX; acoperirea se calculează prin intersecția perechilor unice nume–versiune cu referința, nu prin împărțirea simplă a numărului de componente. Rădăcina Express este afișată separat și exclusă din numitorul procentelor. Procentele PURL/hash/licență au ca numitor dependențele ecosistemului vizat.

| Element | Valoare măsurată |
| --- | --- |
| Node | v20.19.5 |
| npm | 11.17.0 |
| Python | Python 3.12.3 |
| Sistem | Linux x86_64 |
| Cosign | GitVersion:    v3.1.4 |

## 4.3 Rezultate

**Tabelul 4.1 – Express 5.1.0 (npm), referință măsurată: 65 pachete de producție, 368 în total; 390 intrări de lockfile**

| Cfg. | Momentul generării | Syft | Componente npm | Acoperire producție | Acoperire totală | Componente străine | Cu PURL | Cu hash | Cu licență |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Sursă, fără lockfile | 1.18.1 | 0 | 0.0% | 0.0% | 17 acțiuni GitHub (9 unice) | – | – | – |
| B | Sursă, cu lockfile | 1.18.1 | 65 + rădăcina | 100.0% | 17.7% | 17 acțiuni GitHub (9 unice) | 100.0% | 0.0% | 100.0% |
| C | După npm ci --omit=dev | 1.18.1 | 65 + rădăcina | 100.0% | 17.7% | 17 acțiuni GitHub (9 unice) | 100.0% | 0.0% | 100.0% |
| D | După npm ci complet | 1.18.1 | 65 + rădăcina | 100.0% | 17.7% | 23 acțiuni GitHub (15 unice) | 100.0% | 0.0% | 100.0% |
| E | Ca D, inclusiv dezvoltare | 1.18.1 | 368 + rădăcina | 100.0% | 100.0% | 23 acțiuni GitHub (15 unice) | 100.0% | 0.0% | 100.0% |
| F | Ca D | 1.56.0 | 65 + rădăcina | 100.0% | 17.7% | 23 acțiuni GitHub (15 unice); 9 intrări de tip fișier separat | 100.0% | 0.0% | 100.0% |

**Tabelul 4.2 – Flask 3.1.1 (PyPI), referință: 83 perechi în uv.lock și 7 pachete de rulare fixate**

| Cfg. | Momentul generării | Syft | Componente PyPI | Potriviri cu referința | Versiuni corecte de rulare | Cu PURL | Cu hash | Cu licență |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G | Sursă repository | 1.18.1 | 21 | 21 din examples/celery/requirements.txt | 0 din 7 | 100.0% | 0.0% | 0.0% |
| H | Sursă repository | 1.56.0 | 104 | 83 din uv.lock; 21 din examples/celery/requirements.txt | 6 din 7 | 100.0% | 0.0% | 0.0% |
| I | Mediu virtual instalat | 1.18.1 | 8 | 8 din mediu instalat | 7 din 7 | 100.0% | 0.0% | 50.0% |

## 4.4 Interpretarea rezultatelor

Tabelele permit compararea prezenței lockfile-ului (A/B), instalării dependențelor (B/C/D), includerii dezvoltării (D/E), versiunii generatorului (D/F și G/H) și mediului instalat (G/I). O componentă cu nume corect și versiune greșită nu contribuie la acoperire. Componentele GitHub sunt raportate separat de npm; potrivirile PyPI sunt comparate cu uv.lock și cu mediul de rulare. Rezultatele descriu aceste versiuni și această rezolvare a dependențelor, nu toate proiectele npm sau PyPI.

**R1. Lockfile-ul schimbă inventarul din sursă.** În A sunt 0 componente npm, iar în B sunt 65 + rădăcina. Acțiunile GitHub nu substituie inventarul dependențelor npm.

**R2. Dezvoltarea trebuie inclusă explicit.** D are acoperire totală 17.7%, iar E are 100.0%. Diferența dintre referința totală și cea de producție este de 303 perechi nume–versiune.

**R3. Hash-urile lipsesc înainte de post-procesare.** În E, procentul măsurat este 0.0%. Completarea din lockfile este prezentată separat în 4.5, excluzând rădăcina proiectului, care nu are o arhivă de dependență în lockfile.

**R4. Domeniul scanării introduce componente suplimentare.** G include 21 componente din exemplul Celery; H include și pachetele uv.lock. În F, cele 9 intrări suplimentare de tip fișier nu sunt pachete npm și nu sunt numărate drept acțiuni GitHub.

**R5. Mediul influențează metadatele.** I identifică 7 din 7 versiuni de rulare corecte, dar numai 50.0% componente cu licență. Documentul Word raporta 62,5%; rularea actuală folosește alt Python/pip și versiuni de rulare fixate explicit. Această diferență nu a fost eliminată prin ajustarea artificială a rezultatului. Timpii Cosign și dimensiunile artefactelor diferă, de asemenea, față de document.

## 4.5 Completarea hash-urilor

Hash-urile SRI din lockfile sunt convertite din Base64 în hexazecimal și adăugate componentelor npm cu aceeași pereche nume–versiune. Intrările ambigue nu sunt completate automat. Hash-urile existente nu sunt înlocuite. Hash-ul arhivei de pachet nu este hash-ul unui director instalat.

| Configurație | Componente npm | Componente completate | Cu hash după completare |
| --- | --- | --- | --- |
| E | 368 | 368 | 100.0% |
| F | 65 | 65 | 100.0% |

Verificare independentă: arhiva npm pentru `accepts@2.0.0` a fost descărcată și SHA-512 calculat local coincide cu hash-ul adăugat: **True**. SHA-512: `e5cbe0e82b4ac1f81d995a98d562225ca7374356e446a18b8bed96ffa6a8fba63b82efd10b046e021184ce1e41e0a96ccd2b932e0658baa16aa396c89a334a9e`.

## 5.3 Rezultate — semnare cu cheie, fără jurnal

Artefactul de control are 147651 octeți, iar SBOM-ul 359951 octeți. Markerul introdus în T2/T6 este text inofensiv. Testele folosesc operații criptografice Cosign reale. Cheia legitimă și cheia atacatorului sunt distincte. Dezactivarea jurnalului este limitată la acest experiment cu chei locale.

**Tabelul 5.1 – Scenarii și rezultatul verificării**

| Scenariu | Ce s-a modificat | Cheia de verificare | Rezultat | Cod | Conform așteptării |
| --- | --- | --- | --- | --- | --- |
| T0 | Nimic (control) | Legitimă | Acceptat | 0 | Da |
| T1 | Un octet modificat în arhivă | Legitimă | Respins | 1 | Da |
| T2 | Arhivă reconstruită cu marker; semnătură veche | Legitimă | Respins | 1 | Da |
| T3 | Arhivă modificată, semnată de atacator | Legitimă | Respins | 1 | Da |
| T4 | Ca T3, verificare cu cheia atacatorului | Atacator | Acceptat | 0 | Da |
| T5 | Bundle-ul SBOM-ului atașat arhivei | Legitimă | Respins | 1 | Da |
| T6 | Marker introdus înaintea semnării legitime | Legitimă | Acceptat | 0 | Da |

**Performanță – 20 de rulări pentru fiecare operație, timp real incluzând pornirea procesului**

| Operație | Rulări | Media (ms) | Minim (ms) | Maxim (ms) |
| --- | --- | --- | --- | --- |
| sign | 20 | 378.75 | 159.93 | 582.21 |
| verify | 20 | 33.51 | 16.65 | 80.74 |

## 5.4 Interpretarea rezultatelor

T0 este controlul pozitiv. T1 și T2 testează alterarea după semnare, T3 cheia neautorizată, iar T5 asocierea unui bundle cu alt artefact. T4 arată efectul configurării verificatorului să aibă încredere în cheia atacatorului. T6 arată că o semnătură validă poate acoperi un artefact modificat înainte de semnare. Experimentul nu măsoară OIDC, Fulcio, Rekor, verificarea provenienței sau atestări OCI.

## Recomandări

1. Păstrați lockfile-ul folosit drept referință și versiunea generatorului lângă rezultate.
2. Evaluați separat inventarul produsului și inventarul mediului de build, incluzând dezvoltarea explicit când este necesar.
3. Folosiți intersecția nume–versiune pentru acoperire și raportați componentele străine separat.
4. Completați hash-urile dintr-o sursă verificată și păstrați distincția dintre hash de arhivă și hash de fișier.
5. Verificați cu cheia sau identitatea aprobată înainte de deployment; semnarea se completează cu verificarea procesului de build.

Documentație oficială: [configurația Syft](https://oss.anchore.com/docs/reference/syft/configuration/), [semnarea fișierelor cu Cosign](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/).
