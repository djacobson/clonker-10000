# Clonker Recipes (prototype v0.1)

A curated, GitHub-hosted library of **complete Clonker Config v4 configurations**.

## Files

- `index.html` — standalone, responsive recipe browser (no external JavaScript or CSS).
- `index.json` — maintainer-controlled recipe catalog, including titles, descriptions, room summaries, and custom action descriptions.
- `david-roku-denon-starter.json` — first example configuration, copied from the repository's tracked `firmware/clonker/device_config.json` snapshot. **Not verified to match the running Pico.**

## Test locally

From the repository root, run `python -m http.server 8000`, then visit `http://localhost:8000/recipes/` in a browser on the same computer. Alternatively, use GitHub Pages for a hosted prototype (once configured).

Opening `index.html` using `file://` may fail because browsers restrict local JSON fetches.

## Planned import workflow (not implemented)

1. Browse recipes and inspect their descriptions.
2. Select a recipe and send its complete JSON to the Clonker's existing configuration editor.
3. Editor populates its fields without saving automatically.
4. User reviews IP addresses, validates, and explicitly saves using existing revision safeguards.

**No firmware integration exists yet.** This prototype does not contact the Pico or modify configuration. The repository maintainer controls the catalog and its files. Recipes should never be trusted or saved without validation.

## Adding a recipe

1. Add a complete Config v4 JSON file under `recipes/`.
2. Add its entry to the `recipes` array in `index.json`, including a relative `file` path.
3. Test that the JSON parses and is accepted by the Clonker's Config v4 validator before publishing.

Keep this directory outside `firmware/`; it is a web-hosted configuration library, not Pico-deployed code.
