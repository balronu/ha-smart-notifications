# Smart Notifications

Zentrale Verwaltung von Sprachausgaben, Push-Benachrichtigungen und intelligenten Geräteaktionen für Home Assistant.

> **Beta:** `v0.1.0-beta.4` ist eine frühe, installierbare Version. Bitte vor dem produktiven Einsatz sichern und testen.

## Funktionen

- native Config- und Options-Flows
- Ereigniskatalog mit gemeinsamem Nachrichtentext für TTS und Push
- Geräteansicht und Ereignisansicht verwenden dieselbe Konfiguration
- Media-Player als TTS-Ziele und Notify-Entitäten als Push-Ziele
- Best-effort-Erkennung identischer physischer Geräte (z. B. Cast/Music-Assistant-Entitäten) mit manueller Gruppierung bei unklarer Identität
- zentrale Action `smart_notifications.send`
- asynchrone Ausgaben mit grundlegender Fehlerprotokollierung
- bewusste Einzelgeräte- und Ereignistests über Options Flow und Lovelace-Karte
- responsive Smart Notifications Card mit grafischem Editor, Status und Ausgabehistorie

## Installation über HACS

Repository-Kategorie: **Integration**; HACS-Topics sind für die Auffindbarkeit gesetzt.

1. HACS → Integrationen → Benutzerdefiniertes Repository hinzufügen.
2. `https://github.com/balronu/ha-smart-notifications` als **Integration** hinzufügen.
3. Die Beta-Version ausdrücklich auswählen (Pre-Releases aktivieren).
4. Home Assistant neu starten und **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.

## Konfiguration

Nach dem Hinzufügen stehen Optionen für TTS-Engine, Ausgabeentitäten, Ereignistexte und beide Zuordnungsrichtungen zur Verfügung. Eine Entität kann mehreren Ereignissen zugeordnet werden. TTS-Engines wie Piper werden getrennt von Media-Playern erkannt und nie als Lautsprecher angeboten.

Für die Karte die Ressource `/smart_notifications/smart-notifications-card.js` einmalig über **Einstellungen → Dashboards → Ressourcen** als JavaScript-Modul hinzufügen. Die Registrierung ist innerhalb des HA-Lifecycles idempotent; eine bereits vorhandene Ressource wird nicht erneut angelegt. Danach kann **Smart Notifications Card** über den visuellen Karteneditor hinzugefügt werden; YAML ist nicht erforderlich. Testausgaben werden ausschließlich nach einem bewussten Klick und einer Bestätigung ausgeführt.

## Beispielautomation

```yaml
action:
  - action: smart_notifications.send
    data:
      reason: washer_finished
```

## Voraussetzungen und Einschränkungen

- Home Assistant 2026.10 oder neuer (Python 3.14.2+ gemäß dieser HA-Version).
- TTS verwendet die native `tts.speak`-Action; eine TTS-Entität muss konfiguriert sein.
- Push verwendet vorhandene `notify`-Entitäten.
- Kamera-Snapshots, Livevideo, DingDong/Ping, kritische iOS-Alarme, Music-Assistant-Announcements, Ruhezeiten und persistente Warteschlangen sind für spätere Versionen vorgesehen und werden in dieser Beta nicht als verfügbar angeboten.
- Physische Geräte werden best-effort über die Home-Assistant-Geräteidentität erkannt; die Zuordnung muss geprüft werden.
- Es gibt keine produktive Live-VM-Validierung in diesem Release.

## Roadmap

MVP-Erweiterungen: bessere Geräteverwaltung, persistente Historie, Duplikatfenster und robuste Queue-Koordination. Danach optionale Zusatzaktionen und eine Lovelace-Diagnosekarte.

## Fehler melden

Bitte ein Issue mit Home-Assistant-Version, Integration-Version, anonymisiertem Trace und reproduzierbaren Konfigurationsschritten erstellen: https://github.com/balronu/ha-smart-notifications/issues

## English

Smart Notifications centralizes voice announcements, push notifications and intelligent device actions for Home Assistant. The `v0.1.0-beta.4` release adds native nested Options Flow menus with an explicit back-to-main-menu action, complete German and English labels, human-readable device choices, and clear empty-device guidance. Add `/smart_notifications/smart-notifications-card.js` once as a JavaScript module through the dashboard Resources UI, then add the card through its editor. Configure the integration through **Settings → Devices & services** and explicitly enable pre-releases in HACS.

The beta requires Home Assistant 2026.10 or newer (Python 3.14.2+ for this HA line). Camera snapshots/live video, tones, critical iOS alerts, Music Assistant announcements, quiet hours and persistent queues are not implemented yet and are not advertised as supported. Test actions require an explicit click and confirmation. Report issues at the URL above.

## Lizenz

MIT. Siehe [LICENSE](LICENSE).
