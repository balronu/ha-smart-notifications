/* Smart Notifications Card – dependency-free Lit-compatible custom element. */
class SmartNotificationsCard extends HTMLElement {
  setConfig(config) { this.config = config || {}; }
  set hass(value) { this._hass = value; if (!this.shadowRoot) this.attachShadow({mode: "open"}); this.refresh(); }
  get hass() { return this._hass; }
  connectedCallback() { this.refresh(); }
  async refresh() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try { this.data = await this._hass.callApi("GET", "smart_notifications/status"); } catch (error) { this.error = error; }
    this._loading = false; this.render();
  }
  async test(kind, payload) {
    if (!this._hass) return;
    try { await this._hass.callApi("POST", "smart_notifications/test", {kind, ...payload}); await this.refresh(); }
    catch (error) { this.error = error; this.render(); }
  }
  render() {
    if (!this.shadowRoot) return;
    const d = this.data || {devices: [], events: [], history: [], configured: false};
    const title = this.config?.title || "Smart Notifications";
    this.shadowRoot.innerHTML = `<style>
      :host{display:block}ha-card{padding:16px;color:var(--primary-text-color)}h2{margin:0 0 12px;color:var(--primary-color)}
      .status{font-size:.9em;margin-bottom:12px}.ok{color:var(--success-color,#43a047)}.bad{color:var(--error-color,#d32f2f)}
      .row{display:flex;gap:8px;align-items:center;border-top:1px solid var(--divider-color);padding:10px 0;flex-wrap:wrap}.name{flex:1;min-width:170px}.muted{color:var(--secondary-text-color);font-size:.85em}
      button{border:0;border-radius:4px;padding:8px 12px;background:var(--primary-color);color:var(--text-primary-color,#fff);cursor:pointer}input,select{padding:8px;min-width:180px;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:4px}
      .section{margin-top:16px;font-weight:600}.history{max-height:160px;overflow:auto;font-size:.82em}
    </style><ha-card><h2>${this.escape(title)}</h2><div class="status ${d.configured?'ok':'bad'}">${d.configured?'Bereit / Ready':'Nicht konfiguriert / Not configured'}</div>
    <div class="section">Ausgabegeräte / Output devices</div>${d.devices.length?d.devices.map(x=>`<div class="row"><span class="name">${this.escape(x.name)}<br><span class="muted">${this.escape(x.channel)} · ${x.available?'verfügbar / available':'offline'}</span></span><input data-device-message="${this.escape(x.id)}" placeholder="Testnachricht / test message"><button data-device="${this.escape(x.id)}">Testen / Test</button></div>`).join(''):'<div class="muted">Keine Geräte konfiguriert.</div>'}
    <div class="section">Ereignis / Event</div><div class="row"><select id="event">${d.events.map(x=>`<option value="${this.escape(x.id)}">${this.escape(x.name)}</option>`).join('')}</select><button id="event-test">Ereignis testen / Test event</button></div>
    <div class="section">Letzte Ausgaben / Recent outputs</div><div class="history">${d.history.length?d.history.map(x=>`<div>${this.escape(x.timestamp)} · ${this.escape(x.reason)}</div>`).join(''):'Keine Ausgaben / No outputs'}</div>${this.error?`<div class="bad">${this.escape(String(this.error))}</div>`:''}</ha-card>`;
    this.shadowRoot.querySelectorAll('[data-device]').forEach(button=>button.addEventListener('click',()=>{const id=button.dataset.device; const input=this.shadowRoot.querySelector(`[data-device-message="${CSS.escape(id)}"]`); this.test('device',{device_id:id,message:input.value||undefined});}));
    this.shadowRoot.querySelector('#event-test')?.addEventListener('click',()=>this.test('event',{reason:this.shadowRoot.querySelector('#event').value}));
  }
  escape(value) { return String(value??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  static getConfigElement() { return document.createElement('smart-notifications-card-editor'); }
  static getStubConfig() { return {title:'Smart Notifications'}; }
}
class SmartNotificationsCardEditor extends HTMLElement {
  setConfig(config) { this.config = {...config}; this.render(); }
  render() { this.innerHTML = `<label>Title / Titel <input value="${this.config?.title||'Smart Notifications'}"></label>`; this.querySelector('input')?.addEventListener('change', event=>{this.config.title=event.target.value; this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));}); }
}
if (!customElements.get('smart-notifications-card')) customElements.define('smart-notifications-card', SmartNotificationsCard);
if (!customElements.get('smart-notifications-card-editor')) customElements.define('smart-notifications-card-editor', SmartNotificationsCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some(card=>card.type==='smart-notifications-card')) window.customCards.push({type:'smart-notifications-card',name:'Smart Notifications Card',description:'Central output status and deliberate test actions.'});
