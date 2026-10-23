/* Smart Notifications Card – stable Lovelace editor and discovery UI. */
class SmartNotificationsCard extends HTMLElement {
  setConfig(config) { this.config = config || {}; }
  set hass(value) { this._hass = value; if (!this.shadowRoot) this.attachShadow({ mode: "open" }); this.refresh(); }
  get hass() { return this._hass; }
  connectedCallback() { this.refresh(); }
  t(de, en) { return (this._hass?.locale?.language || "de").startsWith("de") ? de : en; }
  async api(method, path, body) { return this._hass.callApi(method, path, body); }

  async refresh(force = false) {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try {
      [this.data, this.discovery] = await Promise.all([
        this.api("GET", "smart_notifications/status"),
        this.api("GET", "smart_notifications/discovery"),
      ]);
      this.error = null;
    } catch (error) { this.error = error; }
    this._loading = false;
    // Do not replace interactive DOM while iOS Safari/WKWebView owns a native
    // select menu. The next safe boundary performs the pending render.
    if (force || (!this._interactionActive && !this._eventEdit)) this.render();
    else this._pendingRender = true;
  }
  async mutate(payload) {
    try { await this.api("POST", "smart_notifications/discovery", payload); await this.refresh(true); }
    catch (error) { this.error = error; this.renderIfSafe(true); }
  }
  renderIfSafe(force = false) { if (force || !this._interactionActive) this.render(); else this._pendingRender = true; }
  finishInteraction() {
    setTimeout(() => {
      this._interactionActive = Boolean(this.shadowRoot?.activeElement);
      if (!this._interactionActive && this._pendingRender) { this._pendingRender = false; if (!this._eventEdit) this.render(); }
    }, 0);
  }
  statusLabel(v) { return ({ new: this.t("Neu", "New"), unchanged: this.t("Unverändert", "Unchanged"), changed: this.t("Geändert", "Changed"), adopted: this.t("Übernommen", "Adopted"), ignored: this.t("Ignoriert", "Ignored"), not_found: this.t("Nicht mehr gefunden", "Missing"), review: this.t("Prüfen", "Review") })[v] || this.t("Unbekannt", "Unknown"); }
  typeLabel(v) { return ({ static: this.t("Statischer Text", "Static text"), template: "Template", parameters: this.t("Laufzeitparameter", "Runtime parameters"), combined: this.t("Kombiniert", "Combined"), tts: "TTS", push: "Push", music_assistant: "Music Assistant", other: this.t("Sonstige", "Other") })[v] || v || this.t("Nicht angegeben", "Not specified"); }
  escape(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  candidates() {
    const q = (this._query || "").toLowerCase(), f = this._filter || "all", groups = new Map();
    (this.discovery?.candidates || []).filter(x => { const h = JSON.stringify(x).toLowerCase(); return (!q || h.includes(q)) && (f === "all" || x.status === f || x.output_type === f || x.source_type === f); }).forEach(x => { const k = x.group_id || x.candidate_id; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(x); });
    return [...groups.values()];
  }
  render() {
    if (!this.shadowRoot) return;
    const d = this.data || { devices: [], events: [], configured: false };
    this.shadowRoot.innerHTML = `<style>:host{display:block}ha-card{padding:16px;color:var(--primary-text-color)}h2{margin:0 0 12px;color:var(--primary-color)}h3{margin:0 0 7px}.section{margin-top:20px;font-weight:600}.muted{color:var(--secondary-text-color);font-size:.86em}.ok{color:var(--success-color,#43a047)}.bad{color:var(--error-color,#d32f2f)}.tools,.row,.devices{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.tools{margin:8px 0}.tools input{flex:1;min-width:160px}.row{border-top:1px solid var(--divider-color);padding:9px 0}.name{flex:1;min-width:170px}.candidate,.event-editor{border:1px solid var(--divider-color);border-radius:6px;margin:8px 0;padding:10px}.pill{display:inline-block;border-radius:12px;padding:2px 8px;margin-right:4px;background:var(--secondary-background-color);font-size:.8em}.detail{background:var(--secondary-background-color);padding:9px;margin-top:8px;overflow-wrap:anywhere}.detail dl{display:grid;grid-template-columns:minmax(120px,30%) 1fr;gap:4px;margin:0}.detail dt{font-weight:600}.detail dd{margin:0}.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px}.form-grid label,.event-editor>label{display:grid;gap:4px}button{border:0;border-radius:4px;padding:8px 12px;background:var(--primary-color);color:var(--text-primary-color,#fff);cursor:pointer}button.secondary{background:var(--secondary-background-color);color:var(--primary-text-color)}input,select,textarea{box-sizing:border-box;padding:8px;min-width:150px;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:4px}textarea{width:100%;min-height:110px;font-family:monospace}@media(max-width:500px){ha-card{padding:12px}.detail dl{grid-template-columns:1fr}.tools>*{width:100%}}</style><ha-card><h2>${this.escape(this.config?.title || "Smart Notifications")}</h2><div class="${d.configured ? "ok" : "bad"}">${d.configured ? this.t("Bereit", "Ready") : this.t("Nicht konfiguriert", "Not configured")}</div><div class="section">${this.t("Ereignisse", "Events")}</div>${this.renderEvents(d)}<div class="section">${this.t("Benachrichtigungen erkennen", "Discover notifications")}</div><div class="muted">${this.escape(this.discovery?.source_scope || this.t("Nur automations.yaml und scripts.yaml; keine privaten Storage-APIs.", "Only automations.yaml and scripts.yaml; no private Storage APIs."))}</div><div class="tools"><input id="search" placeholder="${this.t("Suche nach Name, Text, Ziel oder Quelle", "Search name, text, target or source")}" value="${this.escape(this._query || "")}"><select id="filter"><option value="all">${this.t("Alle", "All")}</option><option value="new">${this.t("Neu", "New")}</option><option value="adopted">${this.t("Übernommen", "Adopted")}</option><option value="changed">${this.t("Geändert", "Changed")}</option><option value="ignored">${this.t("Ignoriert", "Ignored")}</option><option value="tts">TTS</option><option value="push">Push</option><option value="automation">${this.t("Automation", "Automation")}</option><option value="script">${this.t("Skript", "Script")}</option></select><button id="scan">${this.t("Scan starten", "Start scan")}</button></div><div id="candidates">${this.renderCandidates()}</div><div class="section">${this.t("Ausgabegeräte", "Output devices")}</div>${d.devices?.length ? d.devices.map(x => `<div class="row"><span class="name">${this.escape(x.name)}<br><span class="muted">${this.escape(x.channel || "")} · ${x.available ? this.t("verfügbar", "available") : this.t("offline", "offline")}</span></span></div>`).join("") : `<div class="muted">${this.t("Keine Geräte konfiguriert.", "No devices configured.")}</div>`}${this.error ? `<div class="bad">${this.escape(String(this.error))}</div>` : ""}</ha-card>`;
    this.bind();
  }
  renderEvents(d) { const events = d.events || []; return `<div class="tools"><button id="new-event">${this.t("Ereignis hinzufügen", "Add event")}</button></div>${events.length ? events.map(e => `<div class="row"><span class="name"><b>${this.escape(e.name)}</b><br><span class="muted">${this.escape(e.id)} · ${this.typeLabel(e.message_type)} · ${e.enabled ? this.t("aktiv", "enabled") : this.t("deaktiviert", "disabled")}</span></span><button class="secondary" data-edit-event="${this.escape(e.id)}">${this.t("Bearbeiten", "Edit")}</button><button class="secondary" data-test-event="${this.escape(e.id)}">${this.t("Testen", "Test")}</button></div>`).join("") : this.t("Keine Ereignisse", "No events")}${this._eventEdit ? this.renderEventEditor(d) : ""}`; }
  renderEventEditor(d) {
    const e = this._eventEdit.id ? (d.events || []).find(x => x.id === this._eventEdit.id) || this._eventEdit : this._eventEdit, selected = new Set(e.devices || []);
    return `<div class="event-editor"><h3>${e.id ? this.t("Ereignis bearbeiten", "Edit event") : this.t("Ereignis hinzufügen", "Add event")}</h3><div class="form-grid"><label>${this.t("Ereignis-ID", "Event ID")}<input name="event-id" value="${this.escape(e.id || "")}" ${e.id ? "readonly" : ""}></label><label>${this.t("Anzeigename", "Display name")}<input name="event-name" value="${this.escape(e.name || "")}"></label><label>${this.t("Nachrichtentyp", "Message type")}<select name="event-type">${["static", "template", "parameters", "combined"].map(x => `<option value="${x}" ${e.message_type === x ? "selected" : ""}>${this.typeLabel(x)}</option>`).join("")}</select></label><label>${this.t("Priorität", "Priority")}<select name="event-priority">${["low", "normal", "high", "critical"].map(x => `<option value="${x}" ${e.priority === x ? "selected" : ""}>${x}</option>`).join("")}</select></label><label>${this.t("Aktiv", "Enabled")}<input type="checkbox" name="event-enabled" ${e.enabled !== false ? "checked" : ""}></label></div><label>${this.t("Gemeinsamer Nachrichtentext / Template", "Shared message text / template")}<textarea name="event-message">${this.escape(e.message || "")}</textarea></label><label>${this.t("Parameter als JSON", "Parameters as JSON")}<textarea name="event-parameters">${this.escape(JSON.stringify(e.parameters || {}, null, 2))}</textarea></label><div class="muted">${this.t("Unterstützt: states(), state_attr(), now(), if/else und benannte variables.", "Supports: states(), state_attr(), now(), if/else and named variables.")}</div><div class="devices">${(d.devices || []).map(x => `<label><input type="checkbox" data-event-device value="${this.escape(x.id)}" ${selected.has(x.id) ? "checked" : ""}>${this.escape(x.name)}</label>`).join("")}</div><div class="tools"><button id="preview-event" class="secondary">${this.t("Nachrichtenvorschau", "Message preview")}</button><button id="save-event">${this.t("Speichern", "Save")}</button><button id="cancel-event" class="secondary">${this.t("Abbrechen", "Cancel")}</button></div><div id="preview-result" class="detail"></div></div>`;
  }
  renderCandidates() { const groups = this.candidates(); if (!groups.length) return `<div class="muted">${this.t("Noch keine Treffer. Starte einen manuellen Scan.", "No results yet. Start a manual scan.")}</div>`; return groups.map(g => { const i = g[0], s = this._selected === i.candidate_id; return `<article class="candidate"><h3>${this.escape(i.source_name)} <span class="pill">${this.statusLabel(i.status)}</span></h3><div class="muted">${this.escape(i.source_type)} · ${this.escape(i.source_id)} · ${g.length} ${this.t("Ausgabe(n) gruppiert", "output(s) grouped")}</div><div>${this.escape(i.message || this.t("Nachricht nicht eindeutig ermittelbar", "Message not determinable"))}</div><div class="muted">${this.typeLabel(i.message_type)} · ${this.typeLabel(i.output_type)} · ${(i.grouped_targets || []).map(x => this.escape(x)).join(", ") || this.t("Ziel nicht eindeutig ermittelbar", "Target not determinable")}</div><button class="secondary" data-detail="${this.escape(i.candidate_id)}">${this.t("Details prüfen", "Review details")}</button>${s ? this.renderDetail(i, g) : ""}</article>`; }).join(""); }
  renderDetail(i, g) { const matched = new Set(i.device_matches || []); return `<div class="detail"><dl><dt>${this.t("Auslöser", "Trigger")}</dt><dd>${this.escape(i.trigger ? JSON.stringify(i.trigger) : i.source_type === "script" ? this.t("Kein eigener Auslöser (Skript)", "No own trigger (script)") : this.t("Nicht eindeutig ermittelbar", "Not determinable"))}</dd><dt>${this.t("Bedingungen", "Conditions")}</dt><dd>${this.escape(i.conditions ? JSON.stringify(i.conditions) : this.t("Keine Bedingungen angegeben", "No conditions specified"))}</dd><dt>${this.t("Originalnachricht", "Original message")}</dt><dd>${this.escape(i.message || this.t("Nicht eindeutig ermittelbar", "Not determinable"))}</dd><dt>${this.t("Variablen", "Variables")}</dt><dd>${this.escape((i.template_variables || []).join(", ") || this.t("Keine erkannt", "None detected"))}</dd><dt>${this.t("Ausgabearten", "Output types")}</dt><dd>${g.map(x => this.typeLabel(x.output_type)).join(", ")}</dd></dl><div class="muted">${i.missing_devices?.length ? this.t("Nicht konfigurierte Ziele: ", "Unconfigured targets: ") + this.escape(i.missing_devices.join(", ")) : this.t("Alle eindeutig erkannten Ziele sind konfiguriert.", "All clearly detected targets are configured.")}</div><div class="devices">${(this.discovery?.devices || []).map(x => `<label><input type="checkbox" data-adopt-device value="${this.escape(x.id)}" ${matched.has(x.id) ? "checked" : ""}>${this.escape(x.name)}</label>`).join("")}</div><div class="tools"><button data-adopt="${this.escape(i.candidate_id)}">${this.t("Als deaktiviertes Ereignis übernehmen", "Adopt as disabled event")}</button><button class="secondary" data-ignore="${this.escape(i.candidate_id)}">${this.t("Ignorieren", "Ignore")}</button></div></div>`; }
  formPayload() { const r = this.shadowRoot, raw = r.querySelector("[name=event-parameters]")?.value || "{}"; let parameters = {}; try { parameters = JSON.parse(raw); } catch (_) { throw Error(this.t("Parameter müssen gültiges JSON sein.", "Parameters must be valid JSON.")); } return { action: "event_save", reason: r.querySelector("[name=event-id]").value, name: r.querySelector("[name=event-name]").value, message_type: r.querySelector("[name=event-type]").value, message: r.querySelector("[name=event-message]").value, priority: r.querySelector("[name=event-priority]").value, enabled: r.querySelector("[name=event-enabled]").checked, parameters, devices: [...r.querySelectorAll("[data-event-device]:checked")].map(x => x.value) }; }
  async preview() { try { const p = this.formPayload(); delete p.action; const x = await this.api("POST", "smart_notifications/preview", p); this.shadowRoot.querySelector("#preview-result").textContent = x.ok ? x.message : x.error; } catch (e) { this.shadowRoot.querySelector("#preview-result").textContent = String(e); } }
  async saveEvent() { try { await this.mutate(this.formPayload()); this._eventEdit = null; this.renderIfSafe(true); } catch (e) { this.error = e; this.renderIfSafe(true); } }
  bind() {
    const root = this.shadowRoot;
    if (!root._smartNotificationsInteractionBound) {
      root.addEventListener("focusin", () => { this._interactionActive = true; }, { capture: true });
      root.addEventListener("focusout", () => this.finishInteraction(), { capture: true });
      root.addEventListener("pointerdown", () => { this._interactionActive = true; }, { capture: true });
      root.addEventListener("pointerup", () => this.finishInteraction(), { capture: true });
      root._smartNotificationsInteractionBound = true;
    }
    root.querySelector("#scan")?.addEventListener("click", () => this.mutate({ action: "scan" }));
    root.querySelector("#search")?.addEventListener("input", e => { this._query = e.target.value; this.renderIfSafe(); });
    root.querySelector("#filter")?.addEventListener("change", e => { this._filter = e.target.value; this.renderIfSafe(); });
    root.querySelector("#new-event")?.addEventListener("click", () => { this._eventEdit = { message_type: "static", priority: "normal", enabled: false, parameters: {}, devices: [] }; this.renderIfSafe(true); });
    root.querySelectorAll("[data-edit-event]").forEach(b => b.addEventListener("click", () => { this._eventEdit = (this.data.events || []).find(x => x.id === b.dataset.editEvent); this.renderIfSafe(true); }));
    root.querySelectorAll("[data-test-event]").forEach(b => b.addEventListener("click", async () => { try { await this.api("POST", "smart_notifications/test", { kind: "event", reason: b.dataset.testEvent }); } catch (e) { this.error = e; this.renderIfSafe(); } }));
    root.querySelector("#preview-event")?.addEventListener("click", () => this.preview());
    root.querySelector("#save-event")?.addEventListener("click", () => this.saveEvent());
    root.querySelector("#cancel-event")?.addEventListener("click", () => { this._eventEdit = null; this.renderIfSafe(true); });
    root.querySelectorAll("[data-detail]").forEach(b => b.addEventListener("click", () => { this._selected = b.dataset.detail; this.renderIfSafe(true); }));
    root.querySelectorAll("[data-adopt]").forEach(b => b.addEventListener("click", () => this.mutate({ action: "adopt", candidate_id: b.dataset.adopt, edits: { devices: [...root.querySelectorAll("[data-adopt-device]:checked")].map(x => x.value) } })));
    root.querySelectorAll("[data-ignore]").forEach(b => b.addEventListener("click", () => this.mutate({ action: "ignore", candidate_id: b.dataset.ignore })));
  }
  static getConfigElement() { return document.createElement("smart-notifications-card-editor"); }
  static getStubConfig() { return { title: "Smart Notifications" }; }
}
class SmartNotificationsCardEditor extends HTMLElement { setConfig(c) { this.config = { ...c }; this.render(); } render() { this.innerHTML = `<label>Title / Titel <input value="${this.config?.title || "Smart Notifications"}"></label>`; this.querySelector("input")?.addEventListener("change", e => { this.config.title = e.target.value; this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this.config }, bubbles: true, composed: true })); }); } }
if (!customElements.get("smart-notifications-card")) customElements.define("smart-notifications-card", SmartNotificationsCard);
if (!customElements.get("smart-notifications-card-editor")) customElements.define("smart-notifications-card-editor", SmartNotificationsCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type==="smart-notifications-card")) window.customCards.push({ type: "smart-notifications-card", name: "Smart Notifications Card", description: "Discovery, events, previews and output status." });
