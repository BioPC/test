class HPVCPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._hass = null;
    this._narrow = false;
    this._dashboard = null;
    this._viewIndex = 0;
    this._viewEl = null;
    this._loaded = false;
  }
  set hass(value) {
    this._hass = value;
    if (this._viewEl) this._viewEl.hass = value;
    if (!this._loaded && value) this._load();
    this._updateStatus();
  }
  set narrow(value) {
    this._narrow = value;
    if (this._viewEl) this._viewEl.narrow = value;
  }
  set panel(value) { this._panel = value; }
  connectedCallback() { if (this._hass && !this._loaded) this._load(); }
  async _load() {
    this._loaded = true;
    try {
      const response = await fetch('/hpvc_static/dashboard.json?v=1.5.2', {cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      this._dashboard = await response.json();
      await customElements.whenDefined('hui-view');
      this._render();
    } catch (err) {
      this._renderError(err);
    }
  }
  _lovelace() {
    return {
      config: this._dashboard,
      editMode: false,
      mode: 'yaml',
      urlPath: 'home-pv-control',
      enableFullEditMode: false,
      saveConfig: async () => {},
      setEditMode: () => {},
      deleteCard: async () => {},
      duplicateCard: async () => {},
      moveCard: async () => {},
      replaceCard: async () => {},
      editConfig: async () => {},
      deleteBadge: async () => {},
      moveBadge: async () => {},
      replaceBadge: async () => {},
    };
  }
  _render() {
    const css = document.createElement('style');
    css.textContent = `
      :host{display:block;min-height:100%;background:var(--primary-background-color)}
      .top{position:sticky;top:0;z-index:4;display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--app-header-background-color,var(--card-background-color));border-bottom:1px solid var(--divider-color)}
      .title{font-weight:600;margin-right:auto}.tab{border:0;border-radius:18px;padding:8px 13px;background:transparent;color:var(--primary-text-color);cursor:pointer}.tab.active{background:var(--secondary-background-color);font-weight:600}
      .status{font-size:12px;color:var(--secondary-text-color);white-space:nowrap}.content{padding:0 8px 24px}
      @media(max-width:600px){.title{display:none}.status{display:none}.top{justify-content:center}}
    `;
    this.shadowRoot.replaceChildren(css);
    const top=document.createElement('div'); top.className='top';
    const title=document.createElement('div'); title.className='title'; title.textContent='Home PV Control'; top.appendChild(title);
    (this._dashboard.views||[]).forEach((view, index)=>{
      const b=document.createElement('button'); b.className='tab'+(index===this._viewIndex?' active':''); b.textContent=view.title||`View ${index+1}`;
      b.onclick=()=>{this._viewIndex=index;this._render();}; top.appendChild(b);
    });
    const status=document.createElement('div'); status.className='status'; status.id='hpvc-status'; top.appendChild(status);
    this.shadowRoot.appendChild(top);
    const content=document.createElement('div'); content.className='content'; this.shadowRoot.appendChild(content);
    const viewEl=document.createElement('hui-view');
    viewEl.hass=this._hass; viewEl.narrow=this._narrow; viewEl.index=this._viewIndex; viewEl.lovelace=this._lovelace();
    this._viewEl=viewEl; content.appendChild(viewEl); this._updateStatus();
  }
  _updateStatus() {
    const el=this.shadowRoot && this.shadowRoot.getElementById('hpvc-status'); if(!el||!this._hass) return;
    const s=this._hass.states['sensor.hpvc_nodered_status']; el.textContent=s?`Node-RED: ${s.state}`:'Node-RED: checking…';
  }
  _renderError(err) {
    const div=document.createElement('div'); div.style='padding:24px;max-width:760px;margin:auto;color:var(--primary-text-color)';
    div.innerHTML=`<h2>Home PV Control</h2><p>The managed dashboard could not be rendered.</p><p><b>${String(err)}</b></p><p>The original YAML dashboard remains available at <code>/hpvc_static/hpvc_dashboard.yaml</code>, and manual installation is fully supported.</p>`;
    this.shadowRoot.replaceChildren(div);
  }
}
if (!customElements.get('hpvc-panel')) customElements.define('hpvc-panel', HPVCPanel);
