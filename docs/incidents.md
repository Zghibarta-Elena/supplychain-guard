# Analiza tehnică: SolarWinds și XZ Utils

## SolarWinds

Atacatorii au compromis procesul de construire Orion și au introdus SUNBURST în actualizări distribuite prin mecanismul legitim. Compromiterea builder-ului explică de ce o semnătură validă nu este suficientă: organizația poate semna chiar rezultatul malițios.

Lanț conceptual: acces la mediul de build → modificarea rezultatului → semnare și distribuție legitimă → execuție la client. Controale: runner efemer, separarea accesului la sursă/build/release, aprobări independente, monitorizarea builder-ului și compararea cu build-uri independente.

Laborator: `python3 -m supplyguard simulate solarwinds` modifică un fișier text după inventarierea aprobată și detectează schimbarea SHA-256. Nu reproduce malware, accesul inițial sau infrastructura atacatorilor.

Sursă: [MITRE ATT&CK, SolarWinds Compromise](https://attack.mitre.org/campaigns/C0024/).

## XZ Utils

CVE-2024-3094 privește compromiterea distribuțiilor upstream 5.6.0 și 5.6.1. Injecția malițioasă era prezentă în tarball-urile distribuite; impactul depindea de condiții specifice de construire și integrare. Nu toate instalările XZ și nu toate sistemele SSH erau exploatabile.

Lanț conceptual: câștigarea încrederii în mentenanță → includerea intrărilor malițioase în release → activare condiționată la build → bibliotecă afectată. Controale: doi recenzori pentru build/release, inspectarea diferențelor dintre sursa din repository și tarball, verificarea fișierelor generate și inventarierea dependențelor tranzitive.

Laborator: `python3 -m supplyguard simulate xz` adaugă un fișier text numai în varianta de release și îl detectează ca intrare nouă. Nu execută payload-uri, nu modifică biblioteci și nu reproduce exploatarea SSH. Pentru comparații reale trebuie normalizate diferențele legitime produse de procesul de release.

Surse: [Red Hat CVE-2024-3094](https://access.redhat.com/security/cve/cve-2024-3094), [CERT-EU](https://cert.europa.eu/publications/security-advisories/2024-032/).

## Implicații practice

Ambele incidente arată că trebuie protejate atât încrederea în contribuții, cât și transformarea sursei în release. SBOM ajută la identificarea expunerii, iar Sigstore la verificarea originii și integrității. Niciunul nu înlocuiește revizuirea, izolarea build-ului și răspunsul la incidente.

Documentație tehnică: [Syft](https://github.com/anchore/syft), [semnare blob Cosign](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/), [verificare Cosign](https://docs.sigstore.dev/cosign/verifying/verify/).
