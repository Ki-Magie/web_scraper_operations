# web_scraper_operations

## Projektbeschreibung

**web_scraper_operations** ist ein Python-basiertes Projekt, das darauf ausgelegt ist, Websites automatisiert zu bedienen.  
Der Fokus liegt zunächst auf der Automatisierung der PlanSo-Webanwendung mittels Selenium, um manuelle Prozesse zu ersetzen und zu vereinfachen.  

Langfristig soll das Repository um weitere Web-Automatisierungs-Skripte erweitert werden, die unterschiedliche Websites abdecken.

## Architektur & Einsatz

Das Projekt ist als Teil eines größeren Ökosystems gedacht und wird in einem Docker-Image betrieben, das eine Flask-basierte API bereitstellt.  
Diese API bietet verschiedene Endpunkte, die unterschiedliche Automatisierungsfunktionen ausführen.  

`web_scraper_operations` bildet dabei eine Komponente von mehreren innerhalb dieser API.

## Hauptfunktionen

- Automatisches Login bei PlanSo
- Navigation und Interaktion mit PlanSo-Tabellen
- Upload von Dateien in PlanSo über Selenium
- Modularer Aufbau zur einfachen Erweiterung für weitere Websites

## Installation und Setup

1. **Docker-Image bauen und starten**  
   Das repo läuft in einem Docker-Container mit Python, Selenium und ChromeDriver (müssen systemseitig installiert werden)
   Es wird beim erstellen eines neuen Images mit "python_docker" von Github direkt heruntergeladen.
   Der hostinger server hat einen ssh Schlüssle zum Github account.

2. **Konfiguration**  
   - `config.yaml` enthält alle spezifischen Einstellungen für PlanSo (URLs, Selektoren, Tabellen-IDs, etc.)  
   - Zugangsdaten werden zur Laufzeit sicher über Umgebungsvariablen oder API-Aufrufe übergeben  
   - **Wichtig:** Keine Zugangsdaten im Code speichern!

3. **API starten**  
   Die Flask-API startet im Docker-Container und bietet REST-Endpunkte zum Auslösen der Automatisierungsflows.

## Benutzung

Beispielhafter Ablauf zum Upload einer Datei in PlanSo:  

- API-Call an den Endpunkt `planso_upload_flow` mit Benutzername, Passwort und Dateipfad und Tabellen ID.  
- Das Skript öffnet PlanSo, loggt sich ein, navigiert zur Tabelle, lädt die Datei hoch und loggt sich aus.

## Voraussetzungen

- Docker (für den Containerbetrieb)  
- Zugriff auf die PlanSo-Webseite (Netzwerk, Berechtigungen)  
- (Optional) Lokale Python-Umgebung für Entwicklung / Tests mit:  
  - Python 3.12+  
  - `selenium`-Bibliothek  
  - Chrome Browser und kompatibler ChromeDriver (systemseitig)

## Logging

Das Projekt nutzt Python `logging`. Die Konfiguration erfolgt zentral (z.B. in `app.py` des Docker-Images).  
Logs geben detaillierte Infos über jeden Schritt der Automatisierung.

## Erweiterung

Neue Webseiten können durch Implementierung weiterer Klassen ähnlich `PlanSoMain` integriert werden.  
Dabei ist darauf zu achten, dass Konfiguration und Selektoren sauber getrennt und anpassbar bleiben.

---

Bei Fragen oder Problemen gerne melden! :)

---

