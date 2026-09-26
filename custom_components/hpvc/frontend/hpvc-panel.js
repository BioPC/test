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
    this._migrationInfo = null;
    this._migrationBusy = false;
    this._migrationRefreshing = false;
    this._migrationRestarting = false;
    this._legacyPackageRemoving = false;
    this._legacyPackageRemoved = false;
    this._legacyRegistryCleaning = false;
    this._legacyRegistryCleaned = false;
    this._migrationMessage = "";
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
      const migration = await this._getLegacyMigrationInfo();
      if (migration.live.length) {
        this._migrationInfo = migration;
        this._renderMigration();
        return;
      }

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

  _legacyDomains() {
    return [
      "input_boolean",
      "input_button",
      "input_number",
      "input_select",
      "input_text",
    ];
  }

  _isLegacyEntityId(entityId) {
    if (!entityId || !entityId.includes(".")) return false;
    const [domain, objectId] = entityId.split(".", 2);
    return this._legacyDomains().includes(domain) && objectId.startsWith("hpvc_");
  }

  async _storageHelpersForDomain(domain) {
    try {
      const items = await this._hass.callWS({ type: `${domain}/list` });
      return (Array.isArray(items) ? items : [])
        .map((item) => item?.id)
        .filter((id) => typeof id === "string" && id.startsWith("hpvc_"))
        .map((id) => `${domain}.${id}`);
    } catch (_) {
      return [];
    }
  }

  async _getLegacyMigrationInfo() {
    const live = Object.keys(this._hass?.states || {})
      .filter((entityId) => this._isLegacyEntityId(entityId))
      .sort();

    const storageLists = await Promise.all(
      this._legacyDomains().map((domain) => this._storageHelpersForDomain(domain))
    );
    const storage = storageLists.flat().sort();
    const storageSet = new Set(storage);
    const yamlOrRuntime = live.filter((entityId) => !storageSet.has(entityId));

    return {
      live,
      storage,
      yamlOrRuntime,
    };
  }

  _entryId() {
    return (
      this._panel?.config?._panel_custom?.entry_id ||
      this._panel?._panel_custom?.entry_id ||
      this._panel?.config?.entry_id ||
      null
    );
  }

  async _deleteStorageHelper(entityId) {
    const [domain, objectId] = entityId.split(".", 2);
    if (!this._legacyDomains().includes(domain) || !objectId.startsWith("hpvc_")) {
      throw new Error(`Refusing to delete non-legacy entity ${entityId}`);
    }
    return this._hass.callWS({
      type: `${domain}/delete`,
      [`${domain}_id`]: objectId,
    });
  }


  async _runLegacyCleanup() {
    if (this._migrationBusy) return;
    if (!this._hass?.user?.is_admin) {
      this._migrationMessage = "Administrator access is required to delete Home Assistant helpers.";
      this._renderMigration();
      return;
    }

    const info = await this._getLegacyMigrationInfo();
    if (!info.live.length) {
      this._migrationInfo = info;
      this._migrationMessage = "No legacy HPVC helpers remain.";
      this._renderMigration();
      return;
    }

    if (!info.storage.length) {
      this._migrationInfo = info;
      this._migrationMessage =
        `${info.yamlOrRuntime.length} legacy HPVC helper(s) remain, but none are storage-backed. ` +
        "Remove the old HPVC YAML/package definition if it still exists, then restart Home Assistant.";
      this._renderMigration();
      return;
    }

    const confirmed = window.confirm(
      `Delete ${info.storage.length} storage-backed legacy HPVC helper(s)?\n\n` +
      "Only input_boolean.hpvc_*, input_button.hpvc_*, input_number.hpvc_*, input_select.hpvc_* and input_text.hpvc_* are eligible. " +
      "HPVC will not edit Home Assistant .storage files directly. YAML/runtime helpers are handled only by removing their YAML source and restarting Home Assistant."
    );
    if (!confirmed) return;

    this._migrationBusy = true;
    this._migrationMessage = "Cleaning legacy HPVC helpers…";
    this._renderMigration();

    const failures = [];
    for (const entityId of info.storage) {
      try {
        await this._deleteStorageHelper(entityId);
      } catch (err) {
        failures.push(`${entityId}: ${String(err)}`);
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 800));

    const refreshed = await this._getLegacyMigrationInfo();
    this._migrationInfo = refreshed;
    this._migrationBusy = false;

    if (failures.length) {
      this._migrationMessage =
        `${failures.length} helper deletion(s) failed. The remaining entities are shown below.`;
      this._renderMigration();
      return;
    }

    if (refreshed.live.length) {
      this._migrationMessage =
        `${refreshed.live.length} legacy HPVC helper(s) remain. ` +
        "They are YAML/runtime-backed. Remove the old HPVC YAML/package definition if it still exists, then restart Home Assistant.";
      this._renderMigration();
      return;
    }

    this._migrationMessage =
      "Legacy HPVC helpers removed. Reloading Home PV Control into HACS-native mode…";
    this._renderMigration();

    const entryId = this._entryId();
    if (entryId) {
      try {
        await this._hass.callService("homeassistant", "reload_config_entry", {
          entry_id: entryId,
        });
        return;
      } catch (err) {
        this._migrationMessage =
          `Cleanup completed, but automatic HPVC reload failed: ${String(err)}. ` +
          "Reload Home PV Control from Settings → Devices & services.";
        this._renderMigration();
        return;
      }
    }

    this._migrationMessage =
      "Cleanup completed. Reload Home PV Control from Settings → Devices & services.";
    this._renderMigration();
  }

  async _refreshMigration() {
    if (this._migrationRefreshing || this._migrationBusy) return;

    this._migrationRefreshing = true;
    this._migrationMessage = "Refreshing detection…";
    this._renderMigration();

    try {
      this._migrationInfo = await this._getLegacyMigrationInfo();

      if (!this._migrationInfo.live.length) {
        this._migrationRefreshing = false;
        this._migrationMessage = "";
        this._loaded = false;
        await this._load();
        return;
      }

      const count = this._migrationInfo.live.length;
      this._migrationMessage =
        `Detection refreshed — ${count} legacy HPVC helper(s) still found.`;
    } catch (err) {
      this._migrationMessage =
        `Detection refresh failed: ${String(err)}`;
    } finally {
      this._migrationRefreshing = false;
    }

    this._renderMigration();
  }

  async _cleanLegacyRegistry() {
    if (
      this._legacyRegistryCleaning ||
      this._legacyPackageRemoving ||
      this._legacyRegistryCleaning ||
      this._migrationBusy ||
      this._migrationRefreshing ||
      this._migrationRestarting
    ) return;

    if (!this._hass?.user?.is_admin) {
      this._migrationMessage =
        "Administrator access is required to clean legacy HPVC registry entries.";
      this._renderMigration();
      return;
    }

    const info = this._migrationInfo || await this._getLegacyMigrationInfo();
    const confirmed = window.confirm(
      `Remove stale legacy HPVC helper entries from Home Assistant's entity registry?\n\n` +
      `HPVC will target only old standalone input_*.hpvc_* entries with no config entry attached. ` +
      `A JSON backup will be created under /config/hpvc-data/migration-backups/ first.\n\n` +
      `Native HPVC entities, HBC entities, .storage files and runtime-history.json are not edited directly. ` +
      `A Home Assistant restart will still be required afterward.`
    );
    if (!confirmed) return;

    this._legacyRegistryCleaning = true;
    this._migrationMessage = "Backing up and cleaning stale HPVC registry entries…";
    this._renderMigration();

    try {
      await this._hass.callService("hpvc", "clean_legacy_registry");
      this._legacyRegistryCleaned = true;
      this._migrationMessage =
        "Stale legacy HPVC registry entries were backed up and removed. Restart Home Assistant now to unload the remaining legacy helper states.";
    } catch (err) {
      this._migrationMessage =
        `Legacy registry cleanup was not completed: ${String(err)}`;
    } finally {
      this._legacyRegistryCleaning = false;
    }

    this._renderMigration();
  }

  async _backupRemoveLegacyPackage() {
    if (
      this._legacyPackageRemoving ||
      this._migrationBusy ||
      this._migrationRefreshing ||
      this._migrationRestarting
    ) return;

    if (!this._hass?.user?.is_admin) {
      this._migrationMessage =
        "Administrator access is required to remove the legacy HPVC package.";
      this._renderMigration();
      return;
    }

    const confirmed = window.confirm(
      "Back up and remove the standard legacy HPVC package?\n\n" +
      "HPVC will touch ONLY /config/packages/hpvc_config.yaml. " +
      "A timestamped backup will be created under /config/hpvc-data/migration-backups/ first.\n\n" +
      "No other YAML files, .storage files, runtime-history.json, HBC entities, or native HPVC entities will be removed."
    );
    if (!confirmed) return;

    this._legacyPackageRemoving = true;
    this._migrationMessage = "Backing up and removing the legacy HPVC package…";
    this._renderMigration();

    try {
      await this._hass.callService(
        "hpvc",
        "backup_remove_legacy_package"
      );
      this._legacyPackageRemoved = true;
      this._migrationMessage =
        "Legacy HPVC package backed up and removed. Restart Home Assistant to unload the remaining YAML/runtime helpers.";
    } catch (err) {
      this._migrationMessage =
        `Legacy package removal was not completed: ${String(err)}`;
    } finally {
      this._legacyPackageRemoving = false;
    }

    this._renderMigration();
  }

  async _restartHomeAssistantForMigration() {
    if (this._migrationRestarting || this._migrationBusy || this._migrationRefreshing) return;

    if (!this._hass?.user?.is_admin) {
      this._migrationMessage = "Administrator access is required to restart Home Assistant.";
      this._renderMigration();
      return;
    }

    const info = this._migrationInfo || await this._getLegacyMigrationInfo();
    if (!info.yamlOrRuntime.length) {
      this._migrationMessage =
        "No YAML/runtime legacy HPVC helpers are currently detected, so a Home Assistant restart is not required.";
      this._renderMigration();
      return;
    }

    const confirmed = window.confirm(
      `Restart Home Assistant now to unload ${info.yamlOrRuntime.length} YAML/runtime legacy HPVC helper(s)?\n\n` +
      (this._legacyRegistryCleaned
        ? "Stale legacy HPVC registry entries were backed up and removed by HPVC. "
        : this._legacyPackageRemoved
          ? "The standard legacy HPVC package was backed up and removed by HPVC. "
          : "Make sure any old HPVC YAML/package definition has already been removed. ") +
      "Home Assistant will be temporarily unavailable during the restart."
    );
    if (!confirmed) return;

    this._migrationRestarting = true;
    this._migrationMessage = "Restarting Home Assistant…";
    this._renderMigration();

    try {
      await this._hass.callService("homeassistant", "restart");
    } catch (err) {
      this._migrationRestarting = false;
      this._migrationMessage =
        `Home Assistant restart request failed: ${String(err)}`;
      this._renderMigration();
    }
  }

  _renderMigration() {
    const info = this._migrationInfo || { live: [], storage: [], yamlOrRuntime: [] };
    const admin = Boolean(this._hass?.user?.is_admin);
    const sample = info.live.slice(0, 12);
    const more = Math.max(0, info.live.length - sample.length);

    const style = document.createElement("style");
    style.textContent = `
      :host{display:block;min-height:100%;background:var(--primary-background-color);color:var(--primary-text-color)}
      .wrap{max-width:900px;margin:32px auto;padding:0 16px 40px}
      .card{background:var(--card-background-color);border-radius:12px;box-shadow:var(--ha-card-box-shadow);padding:24px}
      h1{margin:0 0 10px;font-size:28px} h2{margin:26px 0 8px;font-size:20px}
      p{line-height:1.55}.warn{padding:12px 14px;border-left:4px solid var(--warning-color,#ff9800);background:var(--secondary-background-color)}
      .ok{padding:12px 14px;border-left:4px solid var(--success-color,#4caf50);background:var(--secondary-background-color)}
      .counts{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}
      .pill{padding:8px 12px;border-radius:999px;background:var(--secondary-background-color);font-weight:600}
      code{font-family:var(--code-font-family,monospace)} ul{line-height:1.55}
      button{border:0;border-radius:6px;padding:11px 16px;margin:8px 8px 0 0;background:var(--primary-color);color:var(--text-primary-color,#fff);font-weight:600;cursor:pointer}
      button.secondary{background:var(--secondary-background-color);color:var(--primary-text-color)}
      button[disabled]{opacity:.55;cursor:not-allowed}
      .msg{margin-top:18px;font-weight:600}
      .small{opacity:.8;font-size:.92em}
    `;

    const wrap = document.createElement("div");
    wrap.className = "wrap";
    const card = document.createElement("div");
    card.className = "card";

    const title = document.createElement("h1");
    title.textContent = "Migrate Manual HPVC to HACS-native";
    card.appendChild(title);

    const intro = document.createElement("p");
    intro.textContent =
      "HPVC detected legacy manual helper entities and has blocked the native control stack for safety. " +
      "This cleanup tool removes only legacy HPVC helper domains and never edits Home Assistant .storage files directly.";
    card.appendChild(intro);

    const counts = document.createElement("div");
    counts.className = "counts";
    counts.innerHTML =
      `<span class="pill">${info.live.length} legacy entities loaded</span>` +
      `<span class="pill">${info.storage.length} storage-backed deletable helpers</span>` +
      `<span class="pill">${info.yamlOrRuntime.length} YAML/runtime helpers</span>`;
    card.appendChild(counts);

    const warning = document.createElement("div");
    warning.className = "warn";
    warning.innerHTML =
      "<b>Migration safety:</b> HPVC can back up and remove stale standalone <code>input_*.hpvc_*</code> " +
      "entity-registry entries through Home Assistant's official registry API. It can also back up/remove only the standard " +
      "<code>/config/packages/hpvc_config.yaml</code> file after administrator confirmation. " +
      "Other YAML files are never deleted automatically, <code>.storage</code> is never edited directly, and " +
      "<code>hpvc-data/runtime-history.json</code> is not deleted.";
    card.appendChild(warning);

    const h2 = document.createElement("h2");
    h2.textContent = "Detected legacy HPVC entities";
    card.appendChild(h2);

    const list = document.createElement("ul");
    for (const entityId of sample) {
      const li = document.createElement("li");
      const code = document.createElement("code");
      code.textContent = entityId;
      li.appendChild(code);
      list.appendChild(li);
    }
    if (more) {
      const li = document.createElement("li");
      li.textContent = `+${more} more`;
      list.appendChild(li);
    }
    card.appendChild(list);

    if (!admin) {
      const adminNote = document.createElement("p");
      adminNote.className = "warn";
      adminNote.textContent =
        "Log in as a Home Assistant administrator to run the cleanup.";
      card.appendChild(adminNote);
    }

    if (info.storage.length) {
      const cleanup = document.createElement("button");
      cleanup.textContent = this._migrationBusy
        ? "Cleaning…"
        : `Delete ${info.storage.length} legacy HPVC helper${info.storage.length === 1 ? "" : "s"} & migrate`;
      cleanup.disabled =
        this._migrationBusy || this._migrationRefreshing || this._migrationRestarting || this._legacyPackageRemoving || this._legacyRegistryCleaning || !admin;
      cleanup.onclick = () => this._runLegacyCleanup();
      card.appendChild(cleanup);
    }

    const refresh = document.createElement("button");
    refresh.className = "secondary";
    refresh.textContent = this._migrationRefreshing
      ? "Refreshing…"
      : "Refresh detection";
    refresh.disabled =
      this._migrationBusy || this._migrationRefreshing || this._migrationRestarting || this._legacyPackageRemoving || this._legacyRegistryCleaning;
    refresh.onclick = () => this._refreshMigration();
    card.appendChild(refresh);

    if (info.yamlOrRuntime.length) {
      if (!this._legacyRegistryCleaned) {
        const cleanRegistry = document.createElement("button");
        cleanRegistry.className = info.storage.length ? "secondary" : "";
        cleanRegistry.textContent = this._legacyRegistryCleaning
          ? "Cleaning stale registry entries…"
          : "Back up & remove stale HPVC registry entries";
        cleanRegistry.disabled =
          this._migrationBusy ||
          this._migrationRefreshing ||
          this._migrationRestarting ||
          this._legacyPackageRemoving ||
          this._legacyRegistryCleaning ||
          !admin;
        cleanRegistry.onclick = () => this._cleanLegacyRegistry();
        card.appendChild(cleanRegistry);
      }

      if (!this._legacyPackageRemoved) {
        const removePackage = document.createElement("button");
        removePackage.className = info.storage.length ? "secondary" : "";
        removePackage.textContent = this._legacyPackageRemoving
          ? "Backing up & removing…"
          : "Back up & remove legacy HPVC package";
        removePackage.disabled =
          this._migrationBusy ||
          this._migrationRefreshing ||
          this._migrationRestarting ||
          this._legacyPackageRemoving ||
          !admin;
        removePackage.onclick = () => this._backupRemoveLegacyPackage();
        card.appendChild(removePackage);
      }

      const restart = document.createElement("button");
      restart.className =
        (info.storage.length || (!this._legacyRegistryCleaned && !this._legacyPackageRemoved))
          ? "secondary"
          : "";
      restart.textContent = this._migrationRestarting
        ? "Restarting Home Assistant…"
        : "Restart Home Assistant";
      restart.disabled =
        this._migrationBusy || this._migrationRefreshing || this._migrationRestarting || !admin;
      restart.onclick = () => this._restartHomeAssistantForMigration();
      card.appendChild(restart);

      const restartHelp = document.createElement("p");
      restartHelp.className = info.storage.length ? "small" : "warn";
      restartHelp.innerHTML = this._legacyRegistryCleaned
        ? "<b>Stale legacy HPVC entity-registry entries have been backed up and removed.</b><br><br>" +
          "Restart Home Assistant to unload the still-running legacy helper states. HPVC will rescan automatically during startup."
        : this._legacyPackageRemoved
          ? "<b>The standard legacy HPVC package has been backed up and removed.</b><br><br>" +
            "Restart Home Assistant to unload YAML/runtime HPVC helpers. HPVC will rescan automatically during startup."
          : info.storage.length
          ? "After deleting storage-backed helpers, remaining YAML/runtime HPVC helpers require a full Home Assistant restart. " +
            "Use <b>Back up & remove legacy HPVC package</b> if the standard package file still exists, then restart Home Assistant."
          : `<b>${info.yamlOrRuntime.length} legacy HPVC helper(s) are still loaded, but none are storage-backed.</b><br><br>` +
            "First use <b>Back up & remove stale HPVC registry entries</b>. This handles old standalone helper entries left in Home Assistant's entity registry. " +
            "Then restart Home Assistant. If the helpers return after restart, an old YAML source is still defining them; " +
            "the standard package can also be removed with <b>Back up & remove legacy HPVC package</b> when present.";
      card.appendChild(restartHelp);
    }

    if (this._migrationMessage) {
      const msg = document.createElement("div");
      msg.className = info.live.length ? "msg warn" : "msg ok";
      msg.textContent = this._migrationMessage;
      card.appendChild(msg);
    }

    const safety = document.createElement("p");
    safety.className = "small";
    safety.innerHTML =
      "Cleanup scope: <code>input_boolean.hpvc_*</code>, <code>input_button.hpvc_*</code>, " +
      "<code>input_number.hpvc_*</code>, <code>input_select.hpvc_*</code> and " +
      "<code>input_text.hpvc_*</code> only. Native <code>switch.hpvc_*</code>, " +
      "<code>number.hpvc_*</code>, <code>text.hpvc_*</code>, <code>select.hpvc_*</code>, " +
      "<code>button.hpvc_*</code>, sensors, binary sensors and HBC entities are never deleted.";
    card.appendChild(safety);

    wrap.appendChild(card);
    this.shadowRoot.replaceChildren(style, wrap);
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
