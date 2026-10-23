# Änderungsprotokoll / Changelog

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
