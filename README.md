# WealthyExile Loot Tracker

Home Assistant custom integration that polls [WealthyExile](https://wealthyexile.com) for your Path of Exile stash value and exposes it as sensors (total value in Divine Orbs, Divines/hour, divine price, top 8 most valuable item stacks, and a sensor per stash tab). Includes an [ESPHome](https://esphome.io) firmware for a Waveshare ESP32-S3-Touch-AMOLED-1.64 display to show it on a dedicated screen next to your keyboard.

## ⚠️ Disclaimer

**This project is entirely AI-generated** (written with Claude Code). Install and use at your own risk. In particular:

- It talks to WealthyExile's internal, undocumented web endpoints (not a published API) by replicating what your browser does. This is inherently fragile: WealthyExile can change their site at any time and break this integration without warning.
- It is **not affiliated with or endorsed by WealthyExile**, Grinding Gear Games, or Path of Exile in any way.
- Your WealthyExile session cookie is stored in Home Assistant's config entry storage on **your own instance**. It is never sent anywhere except directly to wealthyexile.com, but you are trusting your own Home Assistant installation's security with a cookie that has access to your WealthyExile account.
- No warranty of any kind. Nothing here was reviewed by WealthyExile, GGG, or any security professional beyond the author's own testing.

## What it does

- Polls your WealthyExile account every 5 minutes, triggering a real stash sync (same as clicking "Sync" on the website) and reading back the result.
- Exposes the result as Home Assistant sensors: total value (Divine), Divines/hour, current Divine price, session gain, last-synced timestamp, your 8 most valuable item stacks, and one sensor per stash tab (created dynamically based on your actual account — tab count and names vary per account).
- Nothing touches the Path of Exile game client directly — no memory reading, no input injection, no overlay.

## Installation (HACS)

1. In HACS, add this repository as a custom repository (category: Integration).
2. Install "WealthyExile Loot Tracker".
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → "WealthyExile".
5. You'll need two cookies from wealthyexile.com (DevTools → Network tab → any request to `stash?primary=true` → Cookie header): `code_verifier` and a session cookie whose name changes with the current PoE league (e.g. `session-Allflame-1`). The setup form asks for each cookie's name and value separately, since the session cookie's name isn't stable across leagues.

## ESPHome display

See `esphome/wealthyexile-display-164.yaml` for the Waveshare ESP32-S3-Touch-AMOLED-1.64 firmware. Copy `esphome/secrets.yaml.example` to `esphome/secrets.yaml` and fill in your Wi-Fi credentials before compiling. The YAML's `substitutions:` block has placeholder entity IDs — update them to match the actual entity IDs Home Assistant assigns after you set up the integration (Developer Tools → States).

## Known limitations

- WealthyExile's sync-trigger endpoint validates the request against its own server-side state; if something else (e.g. you syncing manually in a browser at the same moment) changes that state between this integration's read and write, one poll can fail. This is expected and self-heals on the next poll — a persistent Home Assistant repair issue only appears after several consecutive failures.
- The hardcoded `next-action`/`x-deployment-id` values in `custom_components/wealthyexile/const.py` are tied to WealthyExile's current deployment and will go stale whenever they redeploy their site. See the comment in that file for how to refresh them.
- The ESPHome firmware has been validated with `esphome config`/`esphome compile` but not yet flashed to real hardware.
