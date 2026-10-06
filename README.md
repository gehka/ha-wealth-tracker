# WealthyExile Loot Tracker

Home Assistant custom integration that polls [WealthyExile](https://wealthyexile.com) for your Path of Exile stash value and exposes it as sensors (total value in Divine Orbs, Divines/hour, divine price, top 8 most valuable item stacks, and a sensor per stash tab). Includes an [ESPHome](https://esphome.io) firmware for a Waveshare ESP32-S3-Touch-AMOLED-1.64 display to show it on a dedicated screen next to your keyboard.

## ⚠️ Disclaimer

**This project is entirely AI-generated** (written with Claude Code). Install and use at your own risk. In particular:

- It talks to WealthyExile's internal, undocumented web endpoints (not a published API) by replicating what your browser does. This is inherently fragile: WealthyExile can change their site at any time and break this integration without warning.
- It is **not affiliated with or endorsed by WealthyExile**, Grinding Gear Games, or Path of Exile in any way.
- Your WealthyExile session cookie is stored in Home Assistant's config entry storage on **your own instance**. It is never sent anywhere except directly to wealthyexile.com, but you are trusting your own Home Assistant installation's security with a cookie that has access to your WealthyExile account.
- No warranty of any kind. Nothing here was reviewed by WealthyExile, GGG, or any security professional beyond the author's own testing.

## What it does

- Polls your WealthyExile account every 5 minutes and reads back whatever stash state is currently there. It never triggers a new sync itself — syncing stays entirely in your hands, either by clicking "Sync" on wealthyexile.com yourself or however WealthyExile syncs during a play session. This is deliberate: there's exactly one source of truth (your WealthyExile account), and this integration only ever reads from it, so it can never race against or interfere with your own activity on the site, and never hammers WealthyExile with sync requests nobody asked for.
- Exposes the result as Home Assistant sensors: total value (Divine), Divines/hour, current Divine price, session gain, last-synced timestamp, your 8 most valuable item stacks, and one sensor per stash tab (created dynamically based on your actual account — tab count and names vary per account).
- Nothing touches the Path of Exile game client directly — no memory reading, no input injection, no overlay.

## Installation (HACS)

1. In HACS, add this repository as a custom repository (category: Integration).
2. Install "WealthyExile Loot Tracker".
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → "WealthyExile".
5. You'll need two cookies from wealthyexile.com (DevTools → Network tab → any request to `stash?primary=true` → Cookie header): `code_verifier` and a session cookie whose name changes with the current PoE league (e.g. `session-Allflame-1`). The setup form asks for each cookie's name and value separately, since the session cookie's name isn't stable across leagues.

## ESPHome display

See `esphome/wealthyexile-display-164.yaml` for the Waveshare ESP32-S3-Touch-AMOLED-1.64 firmware. Copy `esphome/secrets.yaml.example` to `esphome/secrets.yaml` and fill in your Wi-Fi credentials before compiling. The YAML's `substitutions:` block already uses this integration's fixed, predictable entity IDs (see `custom_components/wealthyexile/sensor.py`), so it should work out of the box on a fresh install — worth a quick check under Developer Tools → States after setup just in case something else collided with one of those IDs.

## Known limitations

- The ESPHome firmware has been validated with `esphome config`/`esphome compile` but not yet flashed to real hardware.
