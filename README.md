# Pollenflug Bayern (ePIN LGL) für Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Diese benutzerdefinierte Home-Assistant-Integration liest die Pollenflug-Daten
des **Elektronischen Polleninformationsnetzwerks Bayern (ePIN)** des
[Bayerischen Landesamts für Gesundheit und Lebensmittelsicherheit (LGL)](https://www.lgl.bayern.de/)
aus und stellt sie als Sensoren in Home Assistant bereit – inklusive der
kurzfristigen Vorhersagewerte, die die ePIN-API in 3‑Stunden-Schritten liefert.

> **Hinweis / Disclaimer:** Dies ist ein inoffizielles, privates Community-Projekt.
> Es besteht keine Verbindung zum LGL oder zum Freistaat Bayern. Die Schnittstelle
> ist nicht offiziell dokumentiert; nutze diese Integration auf eigene
> Verantwortung und nicht für sicherheitskritische Entscheidungen (z. B. bei
> starker Pollenallergie/Asthma bitte zusätzlich die offizielle
> [ePIN-App](https://epin.lgl.bayern.de/pollenflug-aktuell) oder ärztlichen Rat nutzen).

## Was macht die Integration?

Für jeden konfigurierten ePIN-Stationscode werden pro erfasster Pollen-/Sporenart
Sensoren angelegt:

- **`sensor.<name>_<pollenart>`** – aktuelle Konzentration (Zustand) sowie als
  Attribut `forecast` die komplette von der API gelieferte Zeitreihe (je
  3‑Stunden-Fenster mit `from`, `to`, `value`) für Diagramme/Automationen.
- **`binary_sensor.<name>_<pollenart>_aktiv`** – `on`, solange im aktuellen
  3‑Stunden-Fenster eine messbare Konzentration vorliegt (praktisch für
  Automationen wie „Fenster zu, solange Birkenpollen fliegen“).
- **`sensor.<name>_letzte_aktualisierung`** – Diagnose-Sensor mit dem
  Zeitstempel des neuesten Datenpunkts der API.

Die Menge der Pollenarten wird **dynamisch** aus der API-Antwort übernommen –
taucht das LGL künftig eine neue Art auf (wie in der Vergangenheit z. B.
Ambrosia), legt die Integration automatisch einen neuen Sensor an, ohne dass
Home Assistant neu gestartet werden muss.

Alle 35 aktuell von der API gelieferten Pollen-/Sporenarten werden mit
deutschem Anzeigenamen dargestellt (z. B. `Betula` → „Birke“); unbekannte,
künftig neu hinzugekommene Arten fallen automatisch auf den lateinischen
Namen zurück.

## Datenquelle

- Stationsliste: `https://epin.lgl.bayern.de/api/locations` (wird beim
  Einrichten der Integration abgefragt, um die Auswahl im Config-Flow zu
  befüllen).
- Messwerte: `https://epin.lgl.bayern.de/api/measurements?locations=<CODE>`
- Auflösung: 3‑Stunden-Fenster, laut API von einem Prognose-Algorithmus
  (`PomoAIv1.34.0` zum Zeitpunkt der Entwicklung) berechnet – die Werte sind
  also bereits Teil einer kurzfristigen Vorhersage, nicht nur reine Rohmessung.
- Einheit: Pollen/Sporen pro Kubikmeter Luft (P/m³), wie in der Aerobiologie üblich.

### Messstation(en) auswählen

Die Integration ruft beim Einrichten die offizielle Stationsliste über
`https://epin.lgl.bayern.de/api/locations` ab und zeigt sie im Config-Flow als
Mehrfachauswahl an – die Stationscodes müssen also **nicht** mehr manuell
gesucht oder eingetippt werden. Aktuell (Stand Einrichtung) liefert die API
diese zwölf Stationen:

| Station | Code | Typ |
|---|---|---|
| Altötting | `DEALTO` | elektronisch |
| Bamberg | `DEBAMB` | manuelle Pollenfalle |
| Feucht | `DEFEUC` | elektronisch |
| Garmisch-Partenkirchen | `DEGARM` | elektronisch |
| Hof | `DEHOF` | elektronisch |
| Marktheidenfeld | `DEMARK` | elektronisch |
| Mindelheim | `DEMIND` | elektronisch |
| München | `DEMUNC` | elektronisch |
| Münnerstadt | `DEMUST` | manuelle Pollenfalle |
| Oberjoch | `DEOBER` | manuelle Pollenfalle |
| Schneefernerhaus (Zugspitze) | `DEUFS` | manuelle Pollenfalle |
| Viechtach | `DEVIEC` | elektronisch |

Du kannst im Auswahldialog mehrere Stationen gleichzeitig wählen – dann legt
die Integration für jede Station ein eigenes Gerät mit eigenen Sensoren an.
Manuelle Pollenfallen werden seltener abgelesen/aktualisiert als die
elektronischen Messstationen; das ist am Gerätemodell in Home Assistant
("… – manuelle Pollenfalle" bzw. "… – elektronisch") erkennbar.

**Fallback:** Ist die Stationsliste beim Einrichten gerade nicht erreichbar
(z. B. Netzwerkproblem), zeigt der Config-Flow stattdessen ein Textfeld zur
manuellen, kommagetrennten Eingabe von Stationscodes (`DEVIEC,DEHOF`, …).

## Installation

### Über HACS (empfohlen)

1. HACS → drei Punkte oben rechts → **Benutzerdefinierte Repositories**.
2. Repository-URL: `https://github.com/GernotAlthammer/ha-pollenflug-bayern`,
   Kategorie **Integration** hinzufügen.
3. „Pollenflug Bayern (ePIN LGL)“ in HACS suchen und installieren.
4. Home Assistant neu starten.

### Manuell

1. Ordner `custom_components/pollenflug_bayern` aus diesem Repository in dein
   Home-Assistant-Verzeichnis `<config>/custom_components/` kopieren.
2. Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen** → „Pollenflug
   Bayern“ suchen.
2. Stationscode(s) eingeben (Standard: `DEVIEC`), optional einen Anzeigenamen
   vergeben.
3. Fertig – die Sensoren werden automatisch angelegt.

Über **Konfigurieren** an der Integration lässt sich das
Abfrageintervall anpassen (Standard: 60 Minuten, minimal 15 Minuten – die
Rohdaten selbst aktualisieren sich ohnehin nur alle 3 Stunden, ein kürzeres
Intervall bringt daher meist keinen Mehrwert und belastet nur die
öffentliche API unnötig).

## Beispiele

### Automation: Fenster schließen bei Birkenpollenflug

```yaml
automation:
  - alias: "Fenster schließen bei Birkenpollenflug"
    trigger:
      - platform: state
        entity_id: binary_sensor.pollenflug_deviec_birke_aktiv
        to: "on"
    action:
      - service: notify.mobile_app_dein_handy
        data:
          title: "Pollenflug"
          message: "Aktuell fliegen Birkenpollen – Fenster besser geschlossen halten."
```

### Template: höchster Vorhersagewert der nächsten Stunden

```yaml
template:
  - sensor:
      - name: "Birkenpollen Höchstwert Vorhersage"
        unit_of_measurement: "P/m³"
        state: >
          {% set forecast = state_attr('sensor.pollenflug_deviec_birke', 'forecast') or [] %}
          {{ (forecast | map(attribute='value') | list | max) if forecast else 'unknown' }}
```

## Einschränkungen

- Die API liefert jeweils die aktuell verfügbaren Zeitfenster (i. d. R. den
  laufenden Tag) – keine mehrtägige Vorhersage über eine gesonderte
  Datumsangabe, da hierzu keine offiziell dokumentierten Parameter bekannt
  sind.
- Die Schnittstelle ist nicht offiziell dokumentiert und kann sich jederzeit
  ändern; Fehlermeldungen/Issues bitte im GitHub-Repository melden.

## Mitwirken

Issues und Pull Requests sind willkommen, insbesondere bestätigte
Stationscodes weiterer ePIN-Standorte (mit Quelle/Nachweis) für die
README-Dokumentation.

## Lizenz

[MIT](LICENSE)
