import "./govee-editor.js?v=1.1.0";

const MARK = "data-govee-paint";
const BRUSH = "M20.71,4.63L19.37,3.29C19,2.9 18.35,2.9 17.96,3.29L9,12.25L11.75,15L20.71,6.04C21.1,5.65 21.1,5 20.71,4.63M7,14A3,3 0 0,0 4,17C4,18.31 2.84,19 2,19C2.92,20.22 4.5,21 6,21A4,4 0 0,0 10,17A3,3 0 0,0 7,14Z";

const SHEET_STYLE = `
  dialog.govee-sheet {
    border: 0;
    padding: 0;
    margin: auto auto 0;
    width: 100%;
    max-width: 640px;
    max-height: 92vh;
    border-radius: 24px 24px 0 0;
    background:
      linear-gradient(var(--ha-card-background, transparent), var(--ha-card-background, transparent)),
      var(--primary-background-color, #fff);
    -webkit-backdrop-filter: blur(30px);
    backdrop-filter: blur(30px);
    color: var(--primary-text-color, #212121);
    overflow: auto;
    box-shadow: 0 -4px 24px rgba(0, 0, 0, .25);
  }
  dialog.govee-sheet::backdrop { background: rgba(0, 0, 0, .45); }
  @media (min-width: 870px) {
    dialog.govee-sheet { margin: auto; border-radius: var(--ha-card-border-radius, 24px); }
  }
  .govee-sheet-head {
    position: sticky; top: 0; z-index: 1;
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px 4px 20px;
    background:
      linear-gradient(var(--ha-card-background, transparent), var(--ha-card-background, transparent)),
      var(--primary-background-color, #fff);
    font-size: 18px; font-weight: 500;
    touch-action: none;
  }
  .govee-sheet-head::before {
    content: ""; position: absolute; left: 50%; top: 6px; width: 36px; height: 4px; margin-left: -18px;
    border-radius: 2px; background: var(--divider-color, rgba(0, 0, 0, .2));
  }
  .govee-sheet-head button {
    width: 40px; height: 40px; border: 0; border-radius: 50%; background: transparent;
    color: inherit; font-size: 22px; cursor: pointer;
  }
  .govee-sheet-head button:focus:not(:focus-visible) { outline: none; }
  .govee-sheet-body { padding: 4px 20px 28px; }
`;

function ensureStyle() {
  if (document.getElementById("govee-sheet-style")) return;
  const style = document.createElement("style");
  style.id = "govee-sheet-style";
  style.textContent = SHEET_STYLE;
  document.head.appendChild(style);
}

function openSheet(hass, entityId, title) {
  ensureStyle();
  const dialog = document.createElement("dialog");
  dialog.className = "govee-sheet";
  const head = document.createElement("div");
  head.className = "govee-sheet-head";
  const name = document.createElement("span");
  name.textContent = title;
  const close = document.createElement("button");
  close.textContent = "×";
  close.setAttribute("aria-label", "Close");
  head.append(name, close);
  const body = document.createElement("div");
  body.className = "govee-sheet-body";
  const editor = document.createElement("govee-segment-editor");
  editor.hass = hass;
  editor.entityId = entityId;
  body.appendChild(editor);
  dialog.append(head, body);
  document.body.appendChild(dialog);
  const done = () => {
    dialog.close();
    dialog.remove();
  };
  close.onclick = done;
  dialog.addEventListener("cancel", (e) => {
    e.preventDefault();
    done();
  });
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) done();
  });
  let startY = null;
  head.addEventListener("pointerdown", (e) => {
    startY = e.clientY;
    head.setPointerCapture(e.pointerId);
  });
  head.addEventListener("pointermove", (e) => {
    if (startY === null) return;
    const dy = Math.max(0, e.clientY - startY);
    dialog.style.transform = `translateY(${dy}px)`;
  });
  head.addEventListener("pointerup", (e) => {
    if (startY === null) return;
    const dy = e.clientY - startY;
    startY = null;
    if (dy > 90) done();
    else dialog.style.transform = "";
  });
  dialog.showModal();
}

function label(hass) {
  return (hass.language || "en").startsWith("fr") ? "Peindre et effets" : "Paint and effects";
}

function inject(element) {
  const hass = element.hass;
  const stateObj = element.stateObj;
  if (!hass || !stateObj || !hass.entities) return;
  const entry = hass.entities[stateObj.entity_id];
  if (!entry || entry.platform !== "govee_light_local") return;
  const root = element.shadowRoot;
  if (!root) return;
  const box = root.querySelector("ha-more-info-control-select-container");
  if (!box || box.querySelector(`[${MARK}]`)) return;
  const button = document.createElement("button");
  button.setAttribute(MARK, "");
  button.style.cssText = [
    "display:inline-flex", "align-items:center", "gap:10px", "height:48px", "border:0",
    "border-radius:var(--ha-border-radius-lg,12px)", "padding:0 18px",
    "background:rgba(139,145,151,.1)", "color:var(--primary-text-color)",
    "font:inherit", "font-size:14px", "cursor:pointer",
  ].join(";");
  button.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" style="fill:currentColor"><path d="${BRUSH}"></path></svg>`;
  button.append(label(hass));
  button.addEventListener("click", () => {
    const title = (element.stateObj && element.stateObj.attributes.friendly_name) || stateObj.entity_id;
    openSheet(element.hass, element.stateObj.entity_id, title);
  });
  box.appendChild(button);
}

customElements.whenDefined("more-info-light").then(() => {
  try {
    const cls = customElements.get("more-info-light");
    if (!cls || cls.prototype.__goveePatched) return;
    const original = cls.prototype.updated;
    cls.prototype.updated = function (changed) {
      if (original) original.call(this, changed);
      try {
        inject(this);
      } catch {}
    };
    cls.prototype.__goveePatched = true;
  } catch {}
});
