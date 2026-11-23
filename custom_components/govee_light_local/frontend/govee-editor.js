const PALETTE = ["#ff2d20", "#ff8a00", "#ffd60a", "#30d158", "#00c7be", "#0a84ff", "#5e5ce6", "#bf5af2", "#ff375f", "#ffffff"];
const MAX_SEGMENTS = 56;
const FALLBACK_LAYER = { mode: 0, pattern: 2, speed: 120, bright: { max: 255, min: 255, kind: 0, rate: 0 }, reverse: false };

const TEXT = {
  en: {
    hint: "Tap or drag to paint",
    segments: (n) => `${n} segments`,
    paint: "Paint",
    effects: "Effects",
    color: "Color",
    tools: "Tools",
    fill: "Fill all",
    gradient: "Gradient",
    clear: "Clear",
    from: "From",
    to: "to",
    apply: "Apply",
    patterns: "My patterns",
    noPatterns: "No pattern yet",
    save: "Save this pattern",
    name: "Pattern name",
    remove: "Delete",
    search: "Search an effect",
    categories: "Categories",
    all: "All",
    effect: "Effect:",
    approx: "approximate preview",
    start: "Start",
    end: "End",
    sent: "Sent to the light",
    failed: "The light does not respond",
    eraser: "Eraser",
    custom: "Other color",
    less: "Fewer segments",
    more: "More segments",
    noScenes: "No effect for this light",
    confirmDelete: (name) => `Delete the pattern "${name}" for everyone?`,
  },
  fr: {
    hint: "Touche ou glisse pour peindre",
    segments: (n) => `${n} segments`,
    paint: "Peindre",
    effects: "Effets",
    color: "Couleur",
    tools: "Outils",
    fill: "Tout remplir",
    gradient: "Dégradé",
    clear: "Effacer",
    from: "De",
    to: "à",
    apply: "Appliquer",
    patterns: "Mes motifs",
    noPatterns: "Aucun motif pour l’instant",
    save: "Enregistrer ce motif",
    name: "Nom du motif",
    remove: "Supprimer",
    search: "Rechercher un effet",
    categories: "Catégories",
    all: "Tout",
    effect: "Effet :",
    approx: "aperçu approximatif",
    start: "Début",
    end: "Fin",
    sent: "Envoyé à la lampe",
    failed: "La lampe ne répond pas",
    eraser: "Gomme",
    custom: "Autre couleur",
    less: "Moins de segments",
    more: "Plus de segments",
    noScenes: "Aucun effet pour cette lampe",
    confirmDelete: (name) => `Supprimer le motif « ${name} » pour tout le monde ?`,
  },
};

const hexToRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const rgbToHex = (rgb) => "#" + rgb.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
const mix = (a, b, t) => a.map((v, k) => v + (b[k] - v) * t);
const scale = (c, f) => c.map((v) => Math.max(0, Math.min(255, v * f)));
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function samplePalette(rgbs, x) {
  if (rgbs.length === 1) return rgbs[0];
  const pos = (((x % 1) + 1) % 1) * rgbs.length;
  const i = Math.floor(pos);
  return mix(rgbs[i], rgbs[(i + 1) % rgbs.length], pos - i);
}

function hash(a, b) {
  const v = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return v - Math.floor(v);
}

function noise(i, t) {
  return (Math.sin(i * 12.9898 + t * 7.1) + Math.sin(i * 4.1414 + t * 13.7) + Math.sin(t * 3.3 + i)) / 3;
}

function layerColor(layer, rgbs, i, n, t) {
  const x = i / n;
  const rate = 0.04 + Math.pow(layer.speed / 255, 2) * 0.5;
  const dir = layer.reverse ? -1 : 1;
  let time = t;
  if (layer.mode === 1) {
    const step = 1 / (rate * 4);
    time = Math.floor(t / step) * step;
  }
  let c;
  if (layer.pattern === 0) {
    c = samplePalette(rgbs, time * rate);
  } else if (layer.pattern === 3) {
    const k = rgbs.length;
    const pos = x * k - dir * time * rate * k;
    c = rgbs[((Math.floor(pos) % k) + k) % k];
  } else if (layer.pattern === 2) {
    c = samplePalette(rgbs, x - dir * time * rate);
  } else {
    c = samplePalette(rgbs, x + time * rate * 0.3);
  }
  let level = 1;
  if (layer.mode === 2) {
    const tick = Math.floor(t * (1 + rate * 8));
    const h = hash(i + 1, tick);
    if (h < 0.72) return [0, 0, 0];
    c = rgbs[Math.floor(hash(tick, i + 7) * rgbs.length)];
    level = (h - 0.72) / 0.28;
  } else if (layer.mode === 3) {
    const head = (((dir * t * rate * 1.5) % 1) + 1) % 1;
    const gap = (((head - x) % 1) + 1) % 1;
    level = Math.max(0, 1 - gap * 5);
  }
  const b = layer.bright;
  const top = b.max / 255;
  const low = Math.min(b.min, b.max) / 255;
  const speedB = 0.2 + (b.rate / 255) * 0.9;
  if (b.kind === 1) level *= low + (top - low) * (0.5 + 0.5 * Math.sin(t * Math.PI * speedB + i * 0.15));
  else if (b.kind === 2) level *= low + (top - low) * Math.pow(Math.max(0, Math.sin(t * Math.PI * speedB)), 8);
  else if (b.kind === 3) level *= Math.max(low, Math.min(1, top * (0.75 + 0.35 * noise(i * 3, t * (1 + speedB * 2)))));
  else level *= top;
  return scale(c, level);
}

function frameColors(scene, n, t) {
  if (!scene.prepared) {
    const layers = scene.anim && scene.anim.length ? scene.anim : [{ ...FALLBACK_LAYER, colors: ["#ffc48c"] }];
    scene.prepared = layers.map((l) => [l, (l.colors && l.colors.length ? l.colors : ["#ffc48c"]).map(hexToRgb)]);
  }
  const out = [];
  for (let i = 0; i < n; i++) {
    let c = [0, 0, 0];
    for (const [layer, rgbs] of scene.prepared) {
      const lc = layerColor(layer, rgbs, i, n, t);
      c = [Math.max(c[0], lc[0]), Math.max(c[1], lc[1]), Math.max(c[2], lc[2])];
    }
    out.push(c);
  }
  return out;
}

function resample(colors, count) {
  if (!colors.length) return Array(count).fill(null);
  return Array.from({ length: count }, (_, j) => colors[Math.min(colors.length - 1, Math.floor(((j + 0.5) * colors.length) / count))]);
}

const STYLE = `
  :host {
    display: block;
    --gse-card: var(--ha-card-background, var(--card-background-color, #fff));
    --gse-text: var(--primary-text-color, #1c1c1e);
    --gse-muted: var(--secondary-text-color, #8e8e93);
    --gse-line: var(--divider-color, rgba(0, 0, 0, 0.12));
    --gse-chip: rgba(127, 127, 127, 0.14);
    --gse-off: rgba(127, 127, 127, 0.28);
    --gse-accent: var(--primary-color, #03a9f4);
    --gse-radius: var(--ha-card-border-radius, 12px);
    color: var(--gse-text);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, inherit));
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  button { font: inherit; color: inherit; }
  header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .sub { color: var(--gse-muted); font-size: 13px; }
  .stepper { display: flex; align-items: center; gap: 6px; color: var(--gse-muted); font-size: 13px; white-space: nowrap; }
  .stepper button { width: 30px; height: 30px; border-radius: 50%; border: 0; background: var(--gse-chip); font-size: 17px; cursor: pointer; }
  .strip { margin: 16px 0 6px; display: grid; gap: 4px; touch-action: none; user-select: none; -webkit-user-select: none; }
  .seg { height: 60px; border-radius: 8px; background: var(--gse-off); transition: background-color .12s; }
  .seg.lit { box-shadow: 0 0 14px -3px var(--glow); }
  .ends { display: flex; justify-content: space-between; color: var(--gse-muted); font-size: 11px; }
  .now { margin-top: 8px; font-size: 13px; min-height: 1.4em; }
  .badge { font-size: 11px; color: var(--gse-muted); border: 1px solid var(--gse-line); border-radius: 999px; padding: 1px 7px; margin-left: 6px; }
  .tabs { display: flex; background: var(--gse-chip); border-radius: 10px; padding: 3px; margin-top: 14px; }
  .tabs button { flex: 1; border: 0; background: transparent; font-size: 14px; padding: 8px 0; border-radius: 8px; cursor: pointer; }
  .tabs button.on { background: var(--gse-card); box-shadow: 0 1px 3px rgba(0, 0, 0, .18); font-weight: 600; }
  .label { margin: 18px 0 10px; font-size: 13px; color: var(--gse-muted); font-weight: 500; }
  .palette { display: flex; flex-wrap: wrap; gap: 10px; }
  .swatch { width: 38px; height: 38px; border-radius: 50%; border: 0; cursor: pointer; outline: 3px solid transparent; outline-offset: 2px; position: relative; padding: 0; }
  .swatch.on { outline-color: var(--gse-accent); }
  .swatch.eraser { background: var(--gse-off); }
  .swatch.eraser::after { content: ""; position: absolute; left: 8px; right: 8px; top: 50%; height: 2px; background: var(--gse-muted); transform: rotate(-45deg); }
  .picker { overflow: hidden; background: conic-gradient(red, yellow, lime, cyan, blue, magenta, red); display: inline-block; }
  .picker input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .chip { border: 0; border-radius: 999px; padding: 9px 14px; cursor: pointer; background: var(--gse-chip); font-size: 14px; display: inline-flex; align-items: center; gap: 8px; }
  .chip.primary, .chip.on { background: var(--gse-accent); color: var(--text-primary-color, #fff); }
  .chip .mini { display: inline-flex; gap: 1px; }
  .chip .mini i { width: 4px; height: 12px; border-radius: 1px; display: block; }
  .chip .x { color: var(--gse-muted); padding-left: 2px; }
  .grad { display: none; margin-top: 12px; }
  .grad.open { display: flex; }
  .grad .swatch { width: 32px; height: 32px; }
  .empty { color: var(--gse-muted); font-size: 13px; }
  .search { width: 100%; border: 0; border-radius: 10px; padding: 11px 12px; background: var(--gse-chip); color: var(--gse-text); font: inherit; outline: none; margin-top: 14px; }
  .cats { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; scrollbar-width: none; }
  .cats::-webkit-scrollbar { display: none; }
  .cats .chip { white-space: nowrap; flex: none; }
  .scenes { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; margin-top: 12px; max-height: 360px; overflow-y: auto; }
  .scene { border: 0; border-radius: 12px; background: var(--gse-chip); text-align: left; padding: 8px; cursor: pointer; font-size: 13px; outline: 2px solid transparent; }
  .scene.on { outline-color: var(--gse-accent); }
  .scene canvas { display: block; width: 100%; height: 16px; margin-bottom: 6px; }
  .hidden { display: none !important; }
  .status { margin-top: 16px; font-size: 12px; color: var(--gse-muted); text-align: center; min-height: 1em; }
`;

class GoveeSegmentEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._entityId = null;
    this._count = 15;
    this._cells = [];
    this._brush = PALETTE[0];
    this._gradA = PALETTE[0];
    this._gradB = PALETTE[5];
    this._gradTarget = "A";
    this._scenes = [];
    this._category = null;
    this._current = null;
    this._patterns = { label: "", patterns: {} };
    this._tab = "paint";
    this._painting = false;
    this._timer = null;
    this._frame = null;
    this._visible = new Set();
    this._observer = new IntersectionObserver((entries) => entries.forEach((e) => (e.isIntersecting ? this._visible.add(e.target) : this._visible.delete(e.target))));
    this._lastTiles = 0;
    this._built = false;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._maybeLoad();
  }

  get hass() {
    return this._hass;
  }

  set entityId(value) {
    if (value === this._entityId) return;
    this._entityId = value;
    this._maybeLoad();
  }

  get entityId() {
    return this._entityId;
  }

  connectedCallback() {
    if (!this._built) this._build();
    this._tilesLoop = (time) => {
      this._drawTiles(time);
      this._tilesFrame = requestAnimationFrame(this._tilesLoop);
    };
    this._tilesFrame = requestAnimationFrame(this._tilesLoop);
  }

  disconnectedCallback() {
    cancelAnimationFrame(this._tilesFrame);
    this._stopPreview();
  }

  get _t() {
    const lang = (this._hass && this._hass.language) || "en";
    return TEXT[lang.split("-")[0]] || TEXT.en;
  }

  _$(id) {
    return this.shadowRoot.getElementById(id);
  }

  _storageKey() {
    return `govee-segment-editor:${this._entityId}`;
  }

  _readCells() {
    try {
      return JSON.parse(localStorage.getItem(this._storageKey())) || [];
    } catch {
      return [];
    }
  }

  _writeCells() {
    try {
      localStorage.setItem(this._storageKey(), JSON.stringify(this._cells));
    } catch {}
  }

  async _maybeLoad() {
    if (!this._hass || !this._entityId) return;
    if (!this._built) this._build();
    const entityId = this._entityId;
    this._stopPreview();
    this._cells = this._readCells();
    this._scenes = [];
    this._renderAll();
    try {
      const [lights, scenes, patterns] = await Promise.all([
        this._hass.callWS({ type: "govee_light_local/lights" }),
        this._hass.callWS({ type: "govee_light_local/scenes", entity_id: entityId }),
        this._hass.callWS({ type: "govee_light_local/patterns" }),
      ]);
      if (entityId !== this._entityId) return;
      const light = lights.find((l) => l.entity_id === entityId);
      this._count = light ? light.segment_count : 15;
      this._scenes = scenes;
      this._patterns = patterns;
    } catch (err) {
      this._status(this._t.failed);
    }
    this._fit();
    this._renderAll();
  }

  _fit() {
    this._cells = Array.from({ length: this._count }, (_, i) => this._cells[i] ?? null);
  }

  _build() {
    const t = this._t;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <header>
        <div class="sub" id="hint"></div>
        <div class="stepper">
          <button id="less">−</button>
          <span id="count"></span>
          <button id="more">+</button>
        </div>
      </header>
      <div class="strip" id="strip"></div>
      <div class="ends"><span id="start"></span><span id="end"></span></div>
      <div class="now" id="now"></div>
      <div class="tabs">
        <button id="tabPaint" class="on"></button>
        <button id="tabEffects"></button>
      </div>
      <div id="paintPane">
        <div class="label" id="lblColor"></div>
        <div class="palette" id="palette"></div>
        <div class="label" id="lblTools"></div>
        <div class="row">
          <button class="chip" id="fill"></button>
          <button class="chip" id="gradient"></button>
          <button class="chip" id="clear"></button>
        </div>
        <div class="row grad" id="gradbox">
          <span class="sub" id="lblFrom"></span><button class="swatch" id="gradA"></button>
          <span class="sub" id="lblTo"></span><button class="swatch" id="gradB"></button>
          <button class="chip" id="gradApply"></button>
        </div>
        <div class="label" id="lblPatterns"></div>
        <div class="row" id="chips"></div>
        <div class="row" style="margin-top:10px"><button class="chip primary" id="save"></button></div>
      </div>
      <div id="effectPane" class="hidden">
        <input class="search" id="search" autocomplete="off">
        <div class="label" id="lblCats"></div>
        <div class="cats" id="cats"></div>
        <div class="scenes" id="scenes"></div>
      </div>
      <div class="status" id="status"></div>
    `;
    this._built = true;
    const strip = this._$("strip");
    strip.addEventListener("pointerdown", (e) => {
      this._painting = true;
      strip.setPointerCapture(e.pointerId);
      this._paintAt(e.clientX, e.clientY);
    });
    strip.addEventListener("pointermove", (e) => this._painting && this._paintAt(e.clientX, e.clientY));
    const end = () => {
      if (!this._painting) return;
      this._painting = false;
      clearTimeout(this._timer);
      this._commit();
    };
    strip.addEventListener("pointerup", end);
    strip.addEventListener("pointercancel", end);
    this._$("less").onclick = () => this._setCount(this._count - 1);
    this._$("more").onclick = () => this._setCount(this._count + 1);
    this._$("fill").onclick = () => this._replace(this._cells.map(() => this._brush));
    this._$("clear").onclick = () => this._replace(this._cells.map(() => null));
    this._$("gradient").onclick = () => {
      this._$("gradbox").classList.toggle("open");
      this._gradTarget = "A";
      this._renderGrad();
    };
    this._$("gradA").onclick = () => { this._gradTarget = "A"; this._renderGrad(); };
    this._$("gradB").onclick = () => { this._gradTarget = "B"; this._renderGrad(); };
    this._$("gradApply").onclick = () => {
      const a = hexToRgb(this._gradA);
      const b = hexToRgb(this._gradB);
      const n = this._count;
      this._replace(this._cells.map((_, i) => rgbToHex(mix(a, b, n === 1 ? 0 : i / (n - 1)))));
    };
    this._$("save").onclick = () => this._savePattern();
    this._$("tabPaint").onclick = () => this._showTab("paint");
    this._$("tabEffects").onclick = () => this._showTab("effects");
    this._$("search").oninput = () => this._renderScenes();
    this._renderAll();
  }

  _renderAll() {
    if (!this._built) return;
    const t = this._t;
    this._$("hint").textContent = t.hint;
    this._$("less").title = t.less;
    this._$("more").title = t.more;
    this._$("start").textContent = t.start;
    this._$("end").textContent = t.end;
    this._$("tabPaint").textContent = t.paint;
    this._$("tabEffects").textContent = t.effects;
    this._$("lblColor").textContent = t.color;
    this._$("lblTools").textContent = t.tools;
    this._$("fill").textContent = t.fill;
    this._$("gradient").textContent = t.gradient;
    this._$("clear").textContent = t.clear;
    this._$("lblFrom").textContent = t.from;
    this._$("lblTo").textContent = t.to;
    this._$("gradApply").textContent = t.apply;
    this._$("lblPatterns").textContent = t.patterns;
    this._$("save").textContent = t.save;
    this._$("search").placeholder = t.search;
    this._$("lblCats").textContent = t.categories;
    this._$("count").textContent = t.segments(this._count);
    this._renderStrip();
    this._renderPalette();
    this._renderGrad();
    this._renderChips();
    this._renderCats();
    this._renderScenes();
  }

  _showTab(tab) {
    this._tab = tab;
    this._$("tabPaint").classList.toggle("on", tab === "paint");
    this._$("tabEffects").classList.toggle("on", tab === "effects");
    this._$("paintPane").classList.toggle("hidden", tab !== "paint");
    this._$("effectPane").classList.toggle("hidden", tab !== "effects");
  }

  _renderStrip() {
    const strip = this._$("strip");
    strip.style.gridTemplateColumns = `repeat(${this._count}, 1fr)`;
    strip.innerHTML = "";
    this._cells.forEach((color, i) => {
      const seg = document.createElement("div");
      seg.className = "seg" + (color ? " lit" : "");
      seg.dataset.i = i;
      if (color) {
        seg.style.background = color;
        seg.style.setProperty("--glow", color);
      }
      strip.appendChild(seg);
    });
  }

  _renderPalette() {
    const t = this._t;
    const box = this._$("palette");
    box.innerHTML = "";
    const eraser = document.createElement("button");
    eraser.className = "swatch eraser" + (this._brush === null ? " on" : "");
    eraser.title = t.eraser;
    eraser.onclick = () => { this._brush = null; this._renderPalette(); };
    box.appendChild(eraser);
    PALETTE.forEach((color) => {
      const b = document.createElement("button");
      b.className = "swatch" + (this._brush === color ? " on" : "");
      b.style.background = color;
      b.onclick = () => this._pick(color);
      box.appendChild(b);
    });
    const custom = document.createElement("label");
    custom.className = "swatch picker" + (this._brush && !PALETTE.includes(this._brush) ? " on" : "");
    custom.title = t.custom;
    const input = document.createElement("input");
    input.type = "color";
    input.value = this._brush || "#ffffff";
    input.oninput = () => this._pick(input.value);
    custom.appendChild(input);
    box.appendChild(custom);
  }

  _pick(color) {
    if (this._$("gradbox").classList.contains("open")) {
      if (this._gradTarget === "A") { this._gradA = color; this._gradTarget = "B"; } else { this._gradB = color; this._gradTarget = "A"; }
      this._renderGrad();
    }
    this._brush = color;
    this._renderPalette();
  }

  _renderGrad() {
    this._$("gradA").style.background = this._gradA;
    this._$("gradB").style.background = this._gradB;
    this._$("gradA").classList.toggle("on", this._gradTarget === "A");
    this._$("gradB").classList.toggle("on", this._gradTarget === "B");
  }

  _renderChips() {
    const t = this._t;
    const box = this._$("chips");
    box.innerHTML = "";
    const names = Object.keys(this._patterns.patterns || {});
    if (!names.length) {
      box.innerHTML = `<span class="empty">${escapeHtml(t.noPatterns)}</span>`;
      return;
    }
    names.forEach((name) => {
      const colors = this._patterns.patterns[name];
      const chip = document.createElement("button");
      chip.className = "chip";
      const mini = colors.slice(0, 20).map((c) => `<i style="background:${c || "var(--gse-off)"}"></i>`).join("");
      chip.innerHTML = `<span class="mini">${mini}</span>${escapeHtml(name)}<span class="x" title="${escapeHtml(t.remove)}">×</span>`;
      chip.onclick = (event) => {
        if (event.target.classList.contains("x")) {
          this._deletePattern(name);
          return;
        }
        this._applyPattern(name);
      };
      box.appendChild(chip);
    });
  }

  _renderCats() {
    const t = this._t;
    const cats = [...new Set(this._scenes.map((s) => s.category).filter(Boolean))];
    const box = this._$("cats");
    box.innerHTML = "";
    [null, ...cats].forEach((c) => {
      const b = document.createElement("button");
      b.className = "chip" + (this._category === c ? " on" : "");
      b.textContent = c ?? t.all;
      b.onclick = () => { this._category = c; this._renderCats(); this._renderScenes(); };
      box.appendChild(b);
    });
  }

  _renderScenes() {
    const box = this._$("scenes");
    box.querySelectorAll("canvas").forEach((c) => { this._observer.unobserve(c); this._visible.delete(c); });
    box.innerHTML = "";
    const q = this._$("search").value.trim().toLowerCase();
    const list = this._scenes.filter((s) => (!this._category || s.category === this._category) && (!q || s.name.toLowerCase().includes(q)));
    if (!list.length) {
      box.innerHTML = `<span class="empty">${escapeHtml(this._t.noScenes)}</span>`;
      return;
    }
    const ratio = window.devicePixelRatio || 1;
    list.forEach((scene) => {
      const b = document.createElement("button");
      b.className = "scene" + (this._current === scene ? " on" : "");
      const canvas = document.createElement("canvas");
      canvas.width = 120 * ratio;
      canvas.height = 16 * ratio;
      canvas.scene = scene;
      b.appendChild(canvas);
      b.appendChild(document.createTextNode(scene.name));
      b.onclick = () => this._playScene(scene, b);
      box.appendChild(b);
      this._observer.observe(canvas);
    });
  }

  _drawTiles(time) {
    if (time - this._lastTiles < 33 || !this._visible.size) return;
    this._lastTiles = time;
    const t = time / 1000;
    const off = getComputedStyle(this).getPropertyValue("--gse-off").trim() || "#888";
    const ratio = window.devicePixelRatio || 1;
    this._visible.forEach((canvas) => {
      const ctx = canvas.getContext("2d");
      const n = 14;
      const w = canvas.width;
      const h = canvas.height;
      const gap = 2 * ratio;
      const cw = (w - gap * (n - 1)) / n;
      ctx.clearRect(0, 0, w, h);
      frameColors(canvas.scene, n, t).forEach((c, i) => {
        ctx.fillStyle = Math.max(...c) > 12 ? rgbToHex(c) : off;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(i * (cw + gap), 0, cw, h, 3 * ratio);
        else ctx.rect(i * (cw + gap), 0, cw, h);
        ctx.fill();
      });
    });
  }

  _animate(time) {
    if (!this._current) return;
    const segs = this._$("strip").children;
    const colors = frameColors(this._current, segs.length, time / 1000);
    for (let i = 0; i < segs.length; i++) {
      const hex = rgbToHex(colors[i]);
      segs[i].style.background = hex;
      segs[i].style.setProperty("--glow", hex);
      segs[i].classList.toggle("lit", Math.max(...colors[i]) > 20);
    }
    this._frame = requestAnimationFrame((tm) => this._animate(tm));
  }

  _stopPreview() {
    if (this._frame) cancelAnimationFrame(this._frame);
    this._frame = null;
    this._current = null;
    if (!this._built) return;
    this._$("now").innerHTML = "";
    this.shadowRoot.querySelectorAll(".scene.on").forEach((el) => el.classList.remove("on"));
  }

  async _playScene(scene, el) {
    this._stopPreview();
    this._current = scene;
    el.classList.add("on");
    this._$("now").innerHTML = `${escapeHtml(this._t.effect)} <b>${escapeHtml(scene.effect)}</b><span class="badge">${escapeHtml(this._t.approx)}</span>`;
    this._frame = requestAnimationFrame((tm) => this._animate(tm));
    if (!this._reachable()) return;
    await this._call(() => this._hass.callService("light", "turn_on", { entity_id: this._entityId, effect: scene.effect }));
  }

  _paintAt(x, y) {
    const el = this.shadowRoot.elementFromPoint(x, y);
    if (!el || !el.classList.contains("seg")) return;
    const i = Number(el.dataset.i);
    if (this._current) {
      this._stopPreview();
      this._renderStrip();
    }
    if (this._cells[i] === this._brush) return;
    this._cells[i] = this._brush;
    const seg = this._$("strip").children[i];
    seg.className = "seg" + (this._brush ? " lit" : "");
    seg.style.background = this._brush || "";
    if (this._brush) seg.style.setProperty("--glow", this._brush);
    this._writeCells();
    clearTimeout(this._timer);
    this._timer = setTimeout(() => this._preview(), 120);
  }

  _preview() {
    this._call(() => this._hass.callWS({ type: "govee_light_local/preview", entity_id: this._entityId, colors: this._cells }), true);
  }

  _commit() {
    return this._call(() => this._hass.callService("govee_light_local", "set_segments", { entity_id: this._entityId, colors: this._cells }));
  }

  _replace(cells) {
    this._stopPreview();
    this._cells = cells;
    this._writeCells();
    this._renderStrip();
    this._commit();
  }

  async _setCount(count) {
    if (count < 1 || count > MAX_SEGMENTS) return;
    this._count = count;
    this._fit();
    this._writeCells();
    this._renderAll();
    await this._call(() => this._hass.callService("govee_light_local", "set_segment_count", { entity_id: this._entityId, count }), true);
  }

  async _refreshPatterns() {
    try {
      this._patterns = await this._hass.callWS({ type: "govee_light_local/patterns" });
    } catch {}
    this._renderChips();
  }

  async _savePattern() {
    const name = (prompt(this._t.name) || "").trim();
    if (!name) return;
    await this._call(() => this._hass.callService("govee_light_local", "save_segment_pattern", { name, colors: this._cells }), true);
    this._refreshPatterns();
  }

  async _deletePattern(name) {
    if (!confirm(this._t.confirmDelete(name))) return;
    await this._call(() => this._hass.callService("govee_light_local", "delete_segment_pattern", { name }), true);
    this._refreshPatterns();
  }

  async _applyPattern(name) {
    this._stopPreview();
    this._cells = resample(this._patterns.patterns[name] || [], this._count);
    this._writeCells();
    this._renderStrip();
    if (!this._reachable()) return;
    await this._call(() => this._hass.callService("light", "turn_on", { entity_id: this._entityId, effect: `${this._patterns.label} · ${name}` }));
  }

  _reachable() {
    const state = this._hass && this._hass.states[this._entityId];
    if (state && state.state !== "unavailable") return true;
    this._status(this._t.failed);
    return false;
  }

  async _call(fn, quiet = false) {
    try {
      await fn();
      if (!quiet) this._status(this._t.sent);
    } catch (err) {
      this._status(this._t.failed);
    }
  }

  _status(text) {
    if (this._built) this._$("status").textContent = text;
  }
}

if (!customElements.get("govee-segment-editor")) {
  customElements.define("govee-segment-editor", GoveeSegmentEditor);
}
