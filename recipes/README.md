# Clonker Recipes

**Less sleek. More CLONK.**

A curated, GitHub-hosted library of complete
**Clonker Config v5 configurations**.

Recipes demonstrate working equipment configurations,
device types, command definitions, room organization,
and Custom Actions.

## Files

- `index.html` — standalone, responsive recipe browser
  with no external JavaScript or CSS dependencies.
- `index.json` — maintainer-controlled recipe catalog,
  including titles, descriptions, room summaries,
  and Custom Action descriptions.
- `david-roku-denon-starter.json` — a complete Config v5
  recipe based on a working configuration exported
  from the physical Clonker.

The catalog's `index_version` is independent of the
Clonker configuration schema version.

## Browse and import

The recipe browser is hosted independently of the
Clonker firmware through GitHub Pages.

1. Open the recipe library using the Clonker
   configuration editor's Browse Recipes control.
2. Select a recipe and review its description.
3. Optionally preview the complete JSON configuration.
4. Download the recipe JSON file.
5. Return to the Clonker configuration editor.
6. Import the downloaded JSON file.
7. Review and customize the configuration.
8. Explicitly save when ready.

Import populates the configuration editor without
automatically saving or executing commands.

A recipe represents a complete configuration,
not an incremental update or room-level merge.

The current configuration revision is retained
for the subsequent save operation.

Saving requires DEVICE + CONFIG mode and remains
subject to firmware validation, revision protection,
and normal persistence safeguards.

## Equipment-specific settings

Always review:

- Room names and device assignments.
- Device types and network endpoints.
- Fundamental command definitions.
- Power and mute ON/OFF commands.
- Custom Action commands and delays.
- Device-specific authentication requirements.

Published device addresses are examples from the
original installation. They are not automatically
substituted during import.

A valid configuration does not necessarily mean
every device is reachable or operational.

## Credentials and future protocols

Never publish live authentication credentials,
client keys, passwords, or access tokens.

For future LG webOS recipes, replace actual client
keys with the explicit placeholder:

`PASTE_OR_PAIR_CLIENT_KEY_HERE`

The placeholder is configuration data, not a usable
authentication credential.

Config v5 supports LG webOS configuration fields,
SSAP commands, structured payloads, and pointer
commands.

Operational LG execution and pairing remain
dependent on future firmware integration.

Apple TV and Amazon Fire TV are reserved future
device types, not currently operational adapters.

## Adding a recipe

1. Start with a complete Config v5 configuration,
   preferably exported from working equipment.
2. Format the JSON for human readability.
3. Preserve stable room, device, and Custom Action
   identifiers.
4. Preserve command definitions, payloads, step
   ordering, and delays.
5. Remove or replace sensitive authentication data.
6. Validate the resulting configuration against
   the active firmware schema.
7. Add the JSON file under `recipes/`.
8. Add its catalog entry to the `recipes` array
   in `index.json`, using a relative file path.
9. Verify preview, download, and editor import.

Document any untested equipment or protocol behavior
rather than implying operational compatibility.

## Test locally

From the repository root, run:

    python -m http.server 8000

Then visit:

    http://localhost:8000/recipes/

Opening `index.html` using `file://` may fail because
browsers restrict local JSON fetches.

## Architectural boundaries

The hosted recipe library:

- Does not contact the Pico directly.
- Does not execute equipment commands.
- Does not automatically save configurations.
- Does not manage live authentication credentials.
- Does not replace firmware-side validation.

Keep this directory outside `firmware/`.

It is an independently hosted configuration library,
not Pico-deployed application code.

## Related documentation

- [Configuration & Recovery](../docs/CONFIGURATION.md)
- [Configuration Redesign](../docs/CONFIGURATION_REDESIGN.md)
- [Operating Modes](../docs/OPERATING_MODES.md)

---

**THE CLONKER 10000**

*Good recipes. Big knobs. More CLONK.*