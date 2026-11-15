# Plan pentru o organizație mică

## Primele 30 de zile

- Responsabilul tehnic inventariază repository-urile, dependențele, runner-ele și persoanele cu drept de publicare.
- Administratorul activează MFA, protecția branch-urilor, revizuirea obligatorie și accesul minim. Modificările workflow-urilor de release au recenzor separat.
- Echipa fixează versiunile dependențelor și acțiunile CI la commit-uri revizuite; automatizează actualizările prin pull request-uri.
- Fiecare release păstrează artefactul, SBOM-ul, semnăturile, asocierea dintre ele și referința commit-ului într-un depozit protejat.
- Persoana care aprobă livrarea verifică semnătura, identitatea, proveniența disponibilă și politica înainte de promovare.

## Operare continuă

Săptămânal: revizuirea alertelor de vulnerabilitate și a schimbărilor de mentenanță pentru dependențe critice. Lunar: revizuirea accesului și testarea restaurării ultimului release aprobat. Trimestrial: exercițiu de revocare a unui release și de reconstruire într-un mediu curat.

Măsurați proporția release-urilor cu SBOM verificat, semnătură verificată și aprobare independentă; timpul până la identificarea consumatorilor unei dependențe afectate; timpul până la retragerea unui release compromis.

## Răspuns la incident

1. Opriți promovarea artefactelor suspecte și izolați runner-ul afectat.
2. Păstrați logurile, hash-urile, SBOM-urile și dovezile de semnare înainte de reconstruire.
3. Identificați versiunile și consumatorii afectați; informați echipele responsabile.
4. Revocați credențialele expuse și verificați accesul la repository, CI și registru.
5. Reconstruiți din sursă revizuită într-un mediu curat; comparați rezultatele și verificați release-ul.
6. Documentați cauza, impactul și controalele corective; testați din nou recuperarea.

Acest proiect este un prototip educațional și un punct de pornire operațional. Controalele pentru infrastructură trebuie configurate efectiv în platformele organizației.
