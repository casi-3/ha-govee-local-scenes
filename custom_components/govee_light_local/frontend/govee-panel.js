import "./govee-editor.js?v=1.1.0b1";

const STYLE = `
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color, #fafafa);
    color: var(--primary-text-color, #212121);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, inherit));
  }
  * { box-sizing: border-box; }
  .toolbar {
    height: var(--header-height, 56px);
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-background-color));
    color: var(--app-header-text-color, var(--primary-text-color));
    border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color, rgba(0, 0, 0, .12)));
    font-size: 20px;
  }
  .menu { display: none; width: 40px; height: 40px; border: 0; border-radius: 50%; background: transparent; color: inherit; cursor: pointer; }
  .menu svg { width: 24px; height: 24px; fill: currentColor; }
  :host([narrow]) .menu { display: inline-flex; align-items: center; justify-content: center; }
  .content { padding: 16px; max-width: 760px; margin: 0 auto; }
  .lamps { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
  .lamp {
    display: flex; align-items: center; gap: 10px; text-align: left; cursor: pointer;
    background: var(--ha-card-background, var(--card-background-color, #fff));
    color: inherit; font: inherit; border: 1px solid var(--divider-color, rgba(0, 0, 0, .12));
    border-radius: var(--ha-card-border-radius, 12px); padding: 10px 14px;
  }
  .lamp.on { border-color: var(--primary-color, #03a9f4); }
  .lamp small { display: block; color: var(--secondary-text-color, #727272); font-size: 12px; }
  .dot { width: 28px; height: 28px; border-radius: 50%; background: conic-gradient(#ff2d20, #ffd60a, #30d158, #0a84ff, #bf5af2, #ff2d20); flex: none; }
  .card {
    background: var(--ha-card-background, var(--card-background-color, #fff));
    border-radius: var(--ha-card-border-radius, 12px);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(0, 0, 0, .12)));
    padding: 16px;
  }
  .empty { color: var(--secondary-text-color, #727272); padding: 24px 0; text-align: center; }
`;

const MENU_ICON = "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z";

class GoveePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._lights = [];
    this._selected = null;
    this._loaded = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._editor) this._build();
    this._editor.hass = hass;
    if (!this._loaded) {
      this._loaded = true;
      this._load();
    }
  }

  set narrow(value) {
    this.toggleAttribute("narrow", Boolean(value));
  }

  set panel(value) {
    this._panel = value;
  }

  _build() {
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="toolbar">
        <button class="menu" id="menu" aria-label="Menu"><svg viewBox="0 0 24 24"><path d="${MENU_ICON}"></path></svg></button>
        <span>Govee</span>
      </div>
      <div class="content">
        <div class="lamps" id="lamps"></div>
        <div class="card" id="card"></div>
      </div>
    `;
    this.shadowRoot.getElementById("menu").onclick = () => {
      this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
    };
    this._editor = document.createElement("govee-segment-editor");
    this.shadowRoot.getElementById("card").appendChild(this._editor);
  }

  async _load() {
    try {
      this._lights = await this._hass.callWS({ type: "govee_light_local/lights" });
    } catch {
      this._lights = [];
    }
    let remembered = null;
    try {
      remembered = localStorage.getItem("govee-panel:selected");
    } catch {}
    const ids = this._lights.map((l) => l.entity_id);
    this._select(ids.includes(remembered) ? remembered : ids[0] || null);
  }

  _select(entityId) {
    this._selected = entityId;
    try {
      if (entityId) localStorage.setItem("govee-panel:selected", entityId);
    } catch {}
    this._renderLamps();
    const card = this.shadowRoot.getElementById("card");
    card.style.display = entityId ? "" : "none";
    if (entityId) this._editor.entityId = entityId;
  }

  _renderLamps() {
    const box = this.shadowRoot.getElementById("lamps");
    box.innerHTML = "";
    if (!this._lights.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = (this._hass.language || "en").startsWith("fr") ? "Aucune lampe Govee détectée" : "No Govee light found";
      box.appendChild(empty);
      return;
    }
    this._lights.forEach((light) => {
      const b = document.createElement("button");
      b.className = "lamp" + (light.entity_id === this._selected ? " on" : "");
      const dot = document.createElement("span");
      dot.className = "dot";
      const text = document.createElement("div");
      text.textContent = light.name;
      const small = document.createElement("small");
      const offline = light.available === false ? ((this._hass.language || "en").startsWith("fr") ? " · hors ligne" : " · offline") : "";
      small.textContent = `${light.sku} · ${light.segment_count} segments${offline}`;
      text.appendChild(small);
      b.append(dot, text);
      b.onclick = () => this._select(light.entity_id);
      box.appendChild(b);
    });
  }
}

if (!customElements.get("govee-panel")) {
  customElements.define("govee-panel", GoveePanel);
}
