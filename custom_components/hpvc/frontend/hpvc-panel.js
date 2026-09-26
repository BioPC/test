class HPVCPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._narrow = false;
    this._panel = null;
    this._route = null;
    this._dashboard = null;
    this._root = null;
    this._fallbackView = null;
    this._loaded = false;
    this._viewIndex = 0;
  }

  set hass(value) {
    this._hass = value;
    if (this._root) this._root.hass = value;
    if (this._fallbackView) this._fallbackView.hass = value;
    if (!this._loaded && value) this._load();
  }

  set narrow(value) {
    this._narrow = value;
    if (this._root) this._root.narrow = value;
    if (this._fallbackView) this._fallbackView.narrow = value;
  }

  set panel(value) {
    this._panel = value;
  }

  set route(value) {
    this._route = value;
    if (this._root) this._root.route = this._lovelaceRoute();
  }

  connectedCallback() {
    if (this._hass && !this._loaded) this._load();
  }

  async _load() {
    this._loaded = true;
    try {
      const response = await fetch("/hpvc_static/dashboard.json?v=1.5.2", {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      this._dashboard = await response.json();

      // loadCardHelpers loads the Lovelace frontend bundle on installations
      // where the dashboard components have not been opened yet.
      if (window.loadCardHelpers) {
        try { await window.loadCardHelpers(); } catch (_) { /* fallback below */ }
      }

      const hasRoot = await Promise.race([
        customElements.whenDefined("hui-root").then(() => true),
        new Promise((resolve) => setTimeout(() => resolve(false), 2500)),
      ]);

      if (hasRoot) this._renderLovelaceRoot();
      else await this._renderFallback();
    } catch (err) {
      this._renderError(err);
    }
  }

  _lovelaceRoute() {
    const prefix = "/home-pv-control";
    let path = window.location.pathname || prefix;
    if (path.startsWith(prefix)) path = path.slice(prefix.length);
    if (!path) path = "/";
    if (!path.startsWith("/")) path = `/${path}`;
    return { prefix, path };
  }

  _lovelace() {
    const config = this._dashboard;
    return {
      config,
      rawConfig: config,
      mode: "yaml",
      urlPath: "home-pv-control",
      editMode: false,
      locale: this._hass?.locale,
      enableFullEditMode: () => {},
      setEditMode: () => {},
      saveConfig: async () => {},
      deleteConfig: async () => {},
      deleteCard: async () => {},
      duplicateCard: async () => {},
      moveCard: async () => {},
      replaceCard: async () => {},
      editConfig: async () => {},
      deleteBadge: async () => {},
      moveBadge: async () => {},
      replaceBadge: async () => {},
      showToast: () => {},
    };
  }

  _lovelacePanelInfo() {
    return {
      component_name: "lovelace",
      url_path: "home-pv-control",
      title: "Home PV Control",
      icon: "mdi:solar-power-variant",
      config: { mode: "yaml" },
    };
  }

  _renderLovelaceRoot() {
    // Use Home Assistant's own Lovelace root instead of a custom HPVC header.
    // This restores the same dashboard header, tabs, section spacing and view
    // rendering used by the v1.5.1 YAML dashboard.
    this.shadowRoot.replaceChildren();
    const root = document.createElement("hui-root");
    root.hass = this._hass;
    root.narrow = this._narrow;
    root.panel = this._lovelacePanelInfo();
    root.lovelace = this._lovelace();
    root.route = this._lovelaceRoute();
    root.noEdit = true;
    this._root = root;
    this.shadowRoot.appendChild(root);
  }

  async _renderFallback() {
    // Compatibility fallback for a frontend where hui-root is not yet exposed.
    await customElements.whenDefined("hui-view");
    this._renderFallbackView();
  }

  _renderFallbackView() {
    const css = document.createElement("style");
    css.textContent = `
      :host{display:block;min-height:100%;background:var(--primary-background-color)}
      .bar{position:sticky;top:0;z-index:4;display:flex;align-items:center;min-height:56px;padding:0 12px;background:var(--app-header-background-color,var(--primary-color));color:var(--app-header-text-color,#fff);box-shadow:var(--ha-card-box-shadow,0 1px 3px rgba(0,0,0,.2))}
      .menu{width:48px;display:flex;align-items:center;justify-content:center;font-size:24px}.tabs{display:flex;align-self:stretch;overflow:auto}.tab{border:0;border-bottom:2px solid transparent;padding:0 18px;background:transparent;color:inherit;font:inherit;cursor:pointer;opacity:.82}.tab.active{border-bottom-color:currentColor;opacity:1;font-weight:600}
      .content{padding:0 8px 24px}
    `;
    this.shadowRoot.replaceChildren(css);
    const bar = document.createElement("div");
    bar.className = "bar";
    const menu = document.createElement("div");
    menu.className = "menu";
    menu.innerHTML = "&#9776;";
    bar.appendChild(menu);
    const tabs = document.createElement("div");
    tabs.className = "tabs";
    (this._dashboard.views || []).forEach((view, index) => {
      const button = document.createElement("button");
      button.className = `tab${index === this._viewIndex ? " active" : ""}`;
      button.textContent = view.title || `View ${index + 1}`;
      button.onclick = () => {
        this._viewIndex = index;
        this._renderFallbackView();
      };
      tabs.appendChild(button);
    });
    bar.appendChild(tabs);
    this.shadowRoot.appendChild(bar);

    const content = document.createElement("div");
    content.className = "content";
    const view = document.createElement("hui-view");
    view.hass = this._hass;
    view.narrow = this._narrow;
    view.index = this._viewIndex;
    view.lovelace = this._lovelace();
    this._fallbackView = view;
    content.appendChild(view);
    this.shadowRoot.appendChild(content);
  }

  _renderError(err) {
    const div = document.createElement("div");
    div.style = "padding:24px;max-width:760px;margin:auto;color:var(--primary-text-color)";
    div.innerHTML = `<h2>Home PV Control</h2><p>The managed dashboard could not be rendered.</p><p><b>${String(err)}</b></p><p>The YAML dashboard remains available at <code>/hpvc_static/hpvc_dashboard.yaml</code>.</p>`;
    this.shadowRoot.replaceChildren(div);
  }
}

if (!customElements.get("hpvc-panel")) customElements.define("hpvc-panel", HPVCPanel);
