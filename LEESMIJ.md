# Wiskundebijles (2de jaar ASO), Python-versie

Een kleine bijlesleraar die lokaal op de Mac draait. Hij legt uit en stelt vragen, maar geeft nooit rechtstreeks het antwoord: zij doet het denkwerk. Er zijn geen extra pakketten nodig, enkel Python 3.9 of nieuwer.

## Eenmalig instellen (in Terminal, in deze map)
```bash
cp .env.example .env
nano .env        # vervang de tekst achter = door je API-sleutel, daarna Ctrl+O, Enter, Ctrl+X
```

## Starten
```bash
python3 server.py
```
Open daarna http://localhost:3000 in de browser. Stoppen kan met Ctrl+C in Terminal.
Handiger: `chmod +x start.command` en dan dubbelklikken op `start.command` in Finder.

## Haar schoolwerk laten analyseren (aanbevolen)
1. Leg foto's of pdf's van huiswerk en gecorrigeerde toetsen in de map `schoolwerk` (maximaal 20).
2. Voer uit: `python3 analyse.py`
3. Lees het nieuwe bestand `werkpunten.md` zelf na en pas het aan waar nodig. De bijlesleraar gebruikt het vanaf het volgende gesprek.

## Het gedrag aanpassen
Alle regels staan in `system-prompt.md`. Pas die tekst gerust aan en open daarna een "Nieuw gesprek".

## Goed om te weten
- De sleutel blijft op deze computer en de server is enkel bereikbaar vanop deze Mac zelf.
- Elk bericht en elke foto kost een klein bedrag via jouw API-sleutel. Stel in de Anthropic Console een maandlimiet in.
- Gesprekken worden niet bewaard, de werkpunten wel.
- Foutmelding over "CERTIFICATE_VERIFY_FAILED" bij een Python van python.org? Dubbelklik in Programma's > Python 3.x op `Install Certificates.command`.
