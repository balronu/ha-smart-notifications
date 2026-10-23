# Änderungsprotokoll / Changelog

## 0.1.0-beta.4 – 2026-10-23

### Deutsch
- Options Flow in native Untermenüs mit „Zurück zum Hauptmenü“ überführt.
- Gespeicherte Optionen bleiben beim Navigieren erhalten; ungespeicherte Formulareingaben werden beim Schließen verworfen.
- Hauptmenüs, Untermenüs, Formularfelder und Prioritäten vollständig auf Deutsch und Englisch beschriftet.
- Geräteauswahl zeigt Anzeigename, Bereich, Integration und Ausgabeart statt doppelter Entity-IDs.
- Leere Gerätelisten liefern eine verständliche Meldung statt leerer Auswahlfelder.
- Echte HA-Übersetzungs-, Navigations- und Persistenz-Regressionstests ergänzt.

### English
- Reworked the Options Flow into native nested menus with an explicit “Back to main menu” action.
- Submitted options persist while navigating; closing a form discards unsaved input.
- Main menus, submenus, form fields and priorities are fully labeled in German and English.
- Device choices show name, area, integration and output channel instead of duplicated entity IDs.
- Empty device lists provide clear guidance instead of empty selectors.
- Added real HA translation, navigation and persistence regression coverage.

## 0.1.0-beta.3 – 2026-10-23

### Deutsch
- Den nachgewiesenen Setup-Fehler durch die reservierte Variable `CONFIG_SCHEMA` behoben.
- Die Beschreibung des Config Flows ist jetzt statisch und kann keinen `device_count`-Formatierungsfehler mehr auslösen.
- TTS-Engines werden aus den tatsächlichen `tts`-States erkannt; Piper bleibt auswählbar.
- Echte HA-Config-Entry-, Config-Flow- und Options-Flow-Regressionstests ergänzt.

### English
- Fixed the proven setup failure caused by the reserved `CONFIG_SCHEMA` module variable.
- The Config Flow description is now static and cannot trigger a `device_count` formatting error.
- TTS engines are discovered from actual `tts` states; Piper remains selectable.
- Added real HA Config Entry, Config Flow and Options Flow regression tests.

## 0.1.0-beta.2 – 2026-10-23

### Deutsch
- Setup-Fehler mit der HA-2026.10-Static-Path-API behoben.
- Options-Flow-Menü auf `menu_options` korrigiert und vollständig übersetzt.
- Technische Feldnamen im Config Flow durch verständliche deutsche und englische Bezeichnungen ersetzt.
- Beta.1-Konfigurationen werden additiv übernommen; TTS-Engines werden getrennt von Ausgabegeräten erkannt.
- Idempotente Service- und Frontend-Registrierung sowie zusätzliche Lifecycle-/Persistenztests.

### English
- Fixed setup failure caused by the HA 2026.10 static-path API.
- Corrected the Options Flow menu to use `menu_options` with complete translations.
- Replaced technical Config Flow field names with clear German and English labels.
- Beta.1 configuration is migrated additively; TTS engines are separated from output devices.
- Added idempotent service/frontend registration and lifecycle/persistence coverage.

## 0.1.0-beta.1 – 2026-10-23

### Deutsch
- Erste installierbare HACS-Beta mit Config Flow und Options Flow.
- Gemeinsame Ereignisnachrichten für TTS und Push.
- Zentrale Action `smart_notifications.send`.
- Best-effort-Duplikatschutz für mehrere Entitäten desselben physischen Geräts.
- Bewusste Einzelgeräte-/Ereignistests und responsive Lovelace-Karte mit Editor.

### English
- First installable HACS beta with Config Flow and Options Flow.
- Shared event messages for TTS and push notifications.
- Central `smart_notifications.send` action.
- Best-effort duplicate suppression for multiple entities of one physical device.
- Deliberate device/event tests and a responsive Lovelace card with editor.
