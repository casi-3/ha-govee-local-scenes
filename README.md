<p align="center">
  <img src="docs/images/icon.png" alt="Govee Local Scenes" width="120">
</p>

<h1 align="center">Govee Local Scenes for Home Assistant</h1>

<p align="center">
  Every scene of the Govee Home app in the Effect menu of your lights, sent over your local network.
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=casi-3&repository=ha-govee-local-scenes&category=integration"><img src="https://img.shields.io/badge/Marketplace-custom%20repository-41BDF5?logo=homeassistant&logoColor=white" alt="Marketplace"></a>
  <a href="https://github.com/casi-3/ha-govee-local-scenes/releases"><img src="https://img.shields.io/github/v/release/casi-3/ha-govee-local-scenes?label=version&color=7E57C2" alt="Version"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2026.10%2B-41BDF5?logo=homeassistant&logoColor=white" alt="Home Assistant 2026.10+">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/casi-3/ha-govee-local-scenes?color=9575CD" alt="Apache 2.0 License"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=casi-3&repository=ha-govee-local-scenes&category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open in the Marketplace"></a>
</p>

<p align="center">
  <img src="docs/images/demo.gif" alt="Picking a scene in Home Assistant lights up the Govee lamp" width="540">
</p>

> [!NOTE]
> You are reading the **1.1 beta**. It adds segment painting, saved patterns and animated effect previews. Feedback is very welcome, for example with a [model feedback](https://github.com/casi-3/ha-govee-local-scenes/issues/new?template=model_feedback.yml).

## ✨ Highlights

- 🌈 **All the scenes**: the built-in Govee lights local integration only knows a handful of scenes per model. This version fills the Effect menu with the full scene catalog of your device, the same one the Govee Home app shows (108 scenes on a Floor Lamp Basic H6076).
- 🏠 **Local control**: scenes are sent straight to the light over the LAN API. No Govee account, no API key, no cloud round trip when you switch scenes.
- 🔁 **Drop-in replacement**: same domain, same config entry, same entities. Your automations, dashboards and entity ids stay as they are.
- 🧩 **Works with any model**: the catalog of the H6076 is bundled. For other models it is downloaded once from Govee's public scene library and kept on disk, after that everything stays local.
- 🖌️ **Paint and effects** (beta): paint each segment by hand, save your own patterns and browse every scene with an animated preview, right from the light dialog.
- 🧱 **No extra dependency**: it uses the same `govee-local-api` package as Home Assistant itself.

## 📦 Installation

> [!IMPORTANT]
> This integration **replaces** the built-in `govee_light_local` integration while it is installed. Home Assistant shows a warning about it in the logs, this is expected.

First enable **LAN Control** for your light in the Govee Home app (device settings).

### With the Marketplace (recommended)

Click the button below, then **Download** and restart Home Assistant. On Home Assistant versions before 2026.11, the same button opens HACS instead.

<a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=casi-3&repository=ha-govee-local-scenes&category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open in the Marketplace"></a>

<details>
<summary>Without the button</summary>

1. In the Marketplace (or HACS), open the menu in the top right corner, then **Custom repositories**.
2. Add `https://github.com/casi-3/ha-govee-local-scenes` with the type **Integration**.
3. Install **Govee Local Scenes** and restart Home Assistant.

</details>

### Manually

1. Copy the `custom_components/govee_light_local` folder into the `custom_components` folder of your Home Assistant configuration.
2. Restart Home Assistant.

If you already use the built-in integration, there is nothing else to do: your lights come back with the new Effect list after the restart. Otherwise add **Govee lights local** from **Settings > Devices & services**.

## 🎨 Usage

<p align="center">
  <img src="docs/images/effects.png" alt="Scenes in the Effect menu of a Govee light" width="420">
</p>

Open a light and pick a scene in the **Effect** menu. Scenes are named `Category · Name`, for example `Natural · Rainbow` or `Festival · Christmas`, and sorted by category.

In automations and scripts:

```yaml
action: light.turn_on
target:
  entity_id: light.floor_lamp
data:
  effect: "Natural · Rainbow"
```

Categories follow the language of your Home Assistant instance when a translation exists (French for now), English otherwise. If a scene name appears twice in the same category, the scene code is added in parentheses.

## 🖌️ Paint and effects (beta)

<p align="center">
  <img src="docs/images/paint-and-effects.png" alt="Paint and effects button in the light dialog, the paint editor and the effect browser" width="900">
</p>

Open any Govee light and tap **Paint and effects**, next to the Effect menu. The editor opens in a sheet with two tabs:

- **Paint**: pick a color and tap or drag over the segments, the light follows live. Fill all, Gradient (two colors, blended from start to end) and Clear do what they say, the eraser clears a segment. The number of segments can be adjusted with the − and + buttons.
- **Effects**: every scene of the light, with search and categories. Each tile plays an animated preview built from the scene data, and tapping it starts the scene on the light. The preview is an approximation: the light computes the real animation itself.

**Patterns**: tap **Save this pattern** to keep a drawing. Saved patterns are shared by all your Govee lights and appear in the regular **Effect** menu as `My patterns · Name`, so they work in scenes, automations and voice assistants like any other effect. A pattern applied to a light with a different number of segments is stretched to fit.

The same editor is also available on a **Govee** page in the sidebar. It can be hidden in **Settings > Devices & services > Govee lights local > Configure**.

### Actions

```yaml
action: govee_light_local.set_segments
target:
  entity_id: light.neon_rope
data:
  colors: ["#ff2d20", "#ff8a00", "#ffd60a", null, "#0a84ff"]
```

Colors are given from the start of the light, one per segment, `null` turns a segment off. Also available: `govee_light_local.save_segment_pattern`, `govee_light_local.delete_segment_pattern` and `govee_light_local.set_segment_count`.

Lights do not report how many segments they have. Known models get the right count automatically (H61D5: 14), other lights start at 15 and can be adjusted in the editor.

## ⚙️ How it works

Govee publishes the scene catalog of each model in a public library used by its app. Each scene comes with a code and, for animated scenes, a parameter block. The integration turns that into the `ptReal` packets the light understands and sends them over UDP to port 4003, exactly like the app does on the local network.

Catalogs are looked up in this order:

1. the catalogs bundled with the integration (`catalogs/<SKU>.json`)
2. the catalogs already downloaded (`.storage/govee_light_local_catalogs/`)
3. a single anonymous HTTPS request to Govee's scene library, saved for next time

If no catalog can be found, the light keeps the scenes of the built-in integration.

## ✅ Confirmed models

| Model | Confirmed by |
| --- | --- |
| H3A53 | [Shmo-jo](https://github.com/Shmo-jo) |
| H6076 | [casi-3](https://github.com/casi-3) |
| H610A | [Shmo-jo](https://github.com/Shmo-jo) |
| H61D5 | [casi-3](https://github.com/casi-3) |
| H6159 | [Shmo-jo](https://github.com/Shmo-jo) |
| H706C | [rafitigay](https://github.com/rafitigay) |
| H8066 | [Shmo-jo](https://github.com/Shmo-jo) |

Thanks to everyone who took the time to test their lights and report back. Other models with LAN control should work the same way. If your model is not listed, whether it works or not, please fill in a [model feedback](https://github.com/casi-3/ha-govee-local-scenes/issues/new?template=model_feedback.yml): it takes a minute and working models are added here with credit to you.

## 🚧 Limitations

- Music mode and DIY scenes are not supported.
- The **Paint and effects** button is added to the light dialog by a small script, because Home Assistant has no official way for an integration to extend that dialog. A future frontend update may hide it until the integration is updated. The Govee page in the sidebar keeps working either way.
- Effect previews are approximate, and the colors of some scenes are guessed from their data.
- The current scene is not read back from the light: if you change it in the Govee app, Home Assistant still shows the last scene it sent.
- This is a snapshot of the built-in integration from Home Assistant 2026.10. Updates to the built-in version are not applied automatically.

## 🗑️ Uninstall

Remove the integration from the Marketplace (or HACS, or delete `custom_components/govee_light_local`) and restart Home Assistant. The built-in integration takes over again with the same config entry.

## 🛠️ Troubleshooting

For detailed logs, add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.govee_light_local: debug
```

A problem or an idea? [Open an issue](https://github.com/casi-3/ha-govee-local-scenes/issues).

## 🙏 Credits

Developed by **casi-3 (casi3)**. Please keep this credit if you reuse or modify this work.

Based on the `govee_light_local` integration of [Home Assistant Core](https://github.com/home-assistant/core). The scene packet format follows the work done in [govee2mqtt](https://github.com/wez/govee2mqtt). See [NOTICE](NOTICE).

This project is not affiliated with Govee.

## 📜 License

[Apache 2.0](LICENSE)
