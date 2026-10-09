# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Gem Collector** — a terminal-based gem prospecting RPG built on **clingine**, a custom CLI engine using Python's `curses` library. The player mines gems, fights enemies, visits shops, and races to $10,000 in lifetime earnings.

## Setup & Running

```bash
# Install dependencies (incl. dev tools) into .venv — dependencies live in pyproject.toml / uv.lock
uv sync

# Run the game
uv run python main.py

# Checks (same as CI: Python 3.13 and 3.14)
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
```

Game code must stay Python 3.13-compatible (the Android toolchain stops at 3.13). See `docs/ROADMAP.md`.

Needs a terminal of at least 80×24; 256 colors recommended (16/8-color terminals get the nearest basic colors). The world view sits above a 3-row HUD; its drawn size comes from the renderer at runtime, capped at the 79×21 simulation view (an 80×24 terminal shows 79×20 of it). Tiles use single-width Unicode glyphs; terminals without UTF-8 get the ASCII ones from `theme.ASCII_FALLBACK`.

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move |
| Space | Use tool / interact with building |
| E | Cycle equipped tool |
| F | Attack nearest enemy |
| R | Use a Recall Charm (teleport to town) |
| Q | Use the most needed supply (Bandage or Lamp Oil) |
| M | World map (explored areas) |
| Esc | Open menu / close sub-screen |
| Enter | Confirm selection |

## Architecture

### Engine (`clingine/`)

**`window.py`** — Central coordinator. Calls `curses.initscr()`, manages `screen_array[y][x] = [is_changed, char, color_pair]`, `window.update()` draws only cells whose content differs from what the terminal already shows (a cell rewritten with the same content costs nothing). Color pairs are lazy-allocated via `window.color_pairs.get_color_pair(((r,g,b),(r,g,b)))`.

**`surface.py`** — Generic off-screen char/color buffer with `blit()` (engine utility; the game world no longer uses it).

**`keyboard.py`** — reads keys via curses `getch()` (no OS hooks or permissions). `poll()` drains pending events once per frame into `pressed` (lowercase key names that fired this frame: new press or OS auto-repeat). Terminals never report releases, so holding a key is a stream of presses; there is no held set.

**`colors.py`** — `ColorPairs`: maps each RGB to the nearest color of the terminal's own palette (xterm 256, or 16/8 ANSI) and caches curses pairs; never redefines terminal colors.

**`util.py`** — `draw_line(renderer, x1, x2, y, char, cp)` and `draw_endpoints(...)`.

**`clock.py`** — `Clock.tick(fps)` sleeps until the next fixed frame deadline (overshoot does not accumulate) and returns the full frame duration.

### Game (`game/`)

| Module | Role |
|--------|------|
| `constants.py` | All magic numbers: MAP_WIDTH=200, MAP_HEIGHT=80, HUD_ROWS=3, VIEW 79×21 (fixed simulation view), FPS=30, biome colors, tile properties, lapidary upgrades, difficulty tiers |
| `data/catalogs.toml` + `objects/registry.py` | Gem (`min_tier`), tool (`tier`) and enemy definitions plus tool-upgrade, bag and lantern tables as data, loaded with stdlib `tomllib` into frozen `GemDef`/`ToolDef`/`EnemyDef` catalogs. File order is catalog order and world generation draws from it — reordering entries changes worlds (bump `WORLDGEN_VERSION`) |
| `state.py` | `GameState` dataclass (incl. bag/lantern/armor/boots levels) — single source of truth for player, world, enemies, inventory, scene |
| `simulation.py` | `new_run(seed)` (fresh GameState: world, player, fog, camera) and `step_game(inp, state, dt)` (one fixed simulation step, no drawing) — same seed + same inputs = same run |
| `loop.py` | `FixedTimestep`: turns frame time into fixed 1/FPS simulation steps (clamped at 0.25 s), buffering pressed input until a step consumes it; `reset()` freezes time outside the game scene |
| `input.py` | `Action` enum, `InputState` (`pressed`/`held` actions), `DEFAULT_KEYMAP`, `map_keys()` — the frontend-agnostic input boundary |
| `tilemap.py` | `TileMap`: the world as data — `meta[(x, y)] = {type, walkable, interactable, depleted, visibility}`, `start_pos`; no glyphs |
| `theme.py` | Terminal theme: `TILE_APPEARANCE` (type → char, colors), depleted/unseen looks, `tile_appearance(meta)` with fog dimming, `ASCII_FALLBACK` |
| `world.py` | `generate_world(seed)` → 200×80 `TileMap` with biomes + town. `ensure_connectivity()` BFS flood-fill. |
| `camera.py` | `update_camera(state)` centers the fixed simulation view on the player (clamped); `on_screen` tests it. `render_view(state, renderer)` → `View` the frontend draws (≤ simulation view); `render_viewport(renderer, state, view)` draws it through `theme.tile_appearance`, touching only changed cells, and sets a sprite per drawn cell (`GROUND` tile type, `OBJECT` gem/bag; enemies and the player set theirs). |
| `hud.py` | `render_hud(renderer, state)` writes to the last three rows: HP (color-coded), Gold, Tool, Biome; the player's tile (`tile_info.describe_here`); key hints or HUD messages (bag fill kept). `HudPulse` (owned by GameScene, render-only) blinks HP/Gold/Bag when they change |
| `events.py` | `emit`/`emit_gem` record world events (finds, damage, healing) in `state.events` (capped, never saved); a frontend `take_events` once per frame and animates them (Kivy: floating text with an icon). The HUD message stays the text record |
| `tips.py` | First-time tips (`check_tips`, run by `step_game`): one mechanic at a time, when it first matters, never over another message, `TIP_GAP` apart; `state.tips_seen` is merged with and saved to the profile by `GameScene` |
| `contracts.py` | Contract board (shop Contracts tab): 3 orders per game day (2 easy gems/loot, 1 any gem) from a stable hash; reward = 1.5x value + 15, skips market saturation, counts as earnings; `contracts_done` saved |
| `deals.py` | Deal of the day: one shop item 25% off per game day, picked from (seed, day) with `decor.stable_random` (no gameplay RNG); banner with countdown in the shop |
| `dog.py` | Companion dog (shop, per run, `has_dog` saved): follows the player, barks (`bark` event + message) when an enemy is within 8 tiles, at most every 10 s; never fights |
| `dowsing.py` | Dowsing rod gear (`[dowsing]` radii): hot/cold + direction hint to the nearest ground gem in the tile row, a `detect` ping event when the trail gets warmer (clues, not map markers) |
| `stats.py` | Lifetime statistics: simulation `bump`s run counters in `state.stats` (not saved); `GameScene.sync_stats` adds the deltas to the profile every 15 s, when the run leaves the game scene and on Android pause; Statistics menu screen |
| `supplies.py` | Consumables (`state.supplies`, data in `catalogs.toml [supplies.*]`): the Item action uses the most needed one (Bandage heals, Lamp Oil refuels) |
| `daylight.py` | Day/night tint by `game_time` (6-minute day; quantized day/dusk/night/dawn tints keep terminal color pairs bounded) with an elliptical lantern glow around the player at night; `shade`/`mix` apply it in every world draw call. Drawing only |
| `landmarks.py` | 7 landmark kinds (campfire, tent, well, mine cart, statue, boat, crystal shrine) placed per seed by stable hash on walkable ground, spaced 15 tiles; drawn like decorations; first visit per run shows lore and may give gold (`visited_landmarks` saved) |
| `weather.py` | Rain showers per 90 s stretch (stable hash of seed + stretch, ~30%); `rain_here` (never in caves) adds an overcast tint via `daylight.phase`; terminal drops in `render_rain`, Kivy streaks + splashes in `RainLayer`. Visual only |
| `decor.py` | Cosmetic decorations (flowers, glowcaps, crystals, reeds, lily pads, pebbles): `decoration(seed, x, y, tile)` hashes the cell, in patches; never stored, so worldgen/saves/simulation are unaffected. Drawn by `camera.render_viewport` (theme `DECOR_APPEARANCE`, sprite = decoration id) and named in the tile row |
| `tile_info.py` | `describe_here(state)`: tile name, what Use does there (enter, dig/pan with which tools, worked out), gem and dropped bag on the tile |
| `player.py` | `init_player`, `update_player` (movement via held move actions, HP regen in town, death check), `render_player`, `set_hud_message` |
| `tools.py` | E cycles tools; Space recovers a dropped bag, picks up visible gems, digs/pans (refused when the bag is full) and rolls drops with the equipped tool's effective tier |
| `gems.py` | `effective_tier(tool, level)`, `roll_gem_drop(biome, tier, rng)` (gems need `min_tier`), bag capacity/count, polished prices (one per gem, highest first), `roll_cut_value`, geodes (`GEODE`, `crack_geode`) |
| `market.py` | All selling: per-kind saturation lowers prices (recovers over game time), `sell_one`/`sell_all`/`preview_sell_all` |
| `fog.py` | `update_fog`: tiles within the lantern's radius and in line of sight (trees, rock and cave walls block it) are visible; recomputed only when the player moves or the light changes (`state.fog_key`) |
| `lantern.py` | Fuel drains per biome, refills in town; `light_radius` sets the fog radius |
| `death.py` | Normal-mode revive in town for a fee with the bag dropped where the player fell (`recover_bag`); hardcore runs end on death |
| `daily.py` | Daily run: seed from the date, 15-minute game-time limit, `daily_end` scene |
| `profile.py` | Progress between runs (`profile.json`): reputation from wins, daily runs and hardcore deaths; first-time tips already shown; outfits owned/worn (`wear_outfit`); perks bought in the Perks menu (`apply_perks` on new normal/hardcore runs, never daily) |
| `achievements.py` | 12 achievements (easy/intermediate/hard, reputation reward proportional to effort), checked by `GameScene` each update, stored in the profile (`unlock_achievements` pays once), announced with a message + `achievement` event; listed in the menu's Achievements screen |
| `bestiary.py` | First sightings of every creature (17 entries) recorded in the profile with where/when (`record_sightings`), announced by `GameScene`; Bestiary menu screen; feeds the Field Notes / Naturalist achievements via `state.seen_species` |
| `bot.py` | Headless greedy bot that plays through `step_game` for balance runs (`scripts/balance_sim.py`, results in `docs/BALANCE.md`) |
| `geography.py` | `in_town(x, y, margin)`, `biome_at(x, y)`, `region_name(x, y)` — the single definition of the town rectangle and biome regions |
| `enemies.py` | `Enemy` class; `find_path_bfs` (parent-pointer BFS, depth cap, falls back to the reachable tile closest to the target, optional `blocked`); `spawn_enemies` (ring around the player: off-screen, out of town, 10 tiles inside the despawn distance), `update_enemies`, `render_enemies`; difficulty scaling |
| `critters.py` | Peaceful animals (`catalogs.toml [[critters]]`: rabbit, deer, bird, frog, fish, firefly, beetle, butterfly, duck, owl, fox, goat, crab, glowworm; optional rain preference, rarity weight, glow): spawn out of sight by biome and time of day, wander, bolt faster than the player when it comes near (herds together); own RNG (`state.critter_rng`), never saved, so gameplay rolls are unchanged |
| `combat.py` | F attack (Chebyshev-1 adjacency, `PLAYER_ATTACK_COOLDOWN`); kills give loot only; enemy auto-attacks on per-enemy cooldown |
| `buildings.py` | `check_building_interaction` (USE on S/L/P tile switches scene) and `check_win` |
| `scenes/` | `SceneManager` + `build_scenes()` registry (one `Scene` per `active_scene` name: `enter`/`update`/`render`); `game.py` (GameScene: fixed-step sim + world drawing), `shop.py` (buy tools/charms, upgrade tools and gear (bag, lantern, armor, boots — `_GEAR`), a description line for the selected row, sell via `market`, Museum donations, Outfits tab: cosmetic palette swaps kept in the profile), `lapidary.py` (LapidaryScene: cutting minigame, geode cracking), `save_point.py` (daily runs can't save), `world_map.py` (M: explored world shrunk to the screen, markers, cached by fog key) |
| `ui.py` | `write_str`, `clear_screen`, `render_list` (paged list with ^/v markers) shared by menus and building screens |
| `persistence.py` | `save_game` (atomic, returns an error message or None), `load_game` (migrates, regenerates world from seed, re-applies depleted tiles/fog; raises `SaveLoadError`), `data_dir()`, leaderboard |
| `menu.py` | Main menu (New Game, Hardcore, Daily Run, Continue, Perks, Achievements, Bestiary, Statistics, Leaderboard), death, win, daily-end, perks and leaderboard screens |

### Mobile (`mobile/`)

`main.py` is the Kivy frontend (Android; also runs on the desktop from `.venv-mobile`, Python 3.13 + Kivy 2.3.1): a `GridRenderer` (80x24 cells, redraws changed cells; draws the pixel-art from `sprites.py` where the game sets sprites, glyphs elsewhere), floating event text, particle bursts per event kind (`particles.py`: sparkles, dust, sparks, blood, loot, heal), sound effects synthesized by `sfx.py` (one per event kind plus a button tap; the shop emits `coin`/`denied` events, cached as WAV in the app's data dir; a Settings popup (`settings.py`, saved in `preferences.json`: sound effects, ambience, button clicks, vibration, screen shake 100/50/0%, reduce motion), Android vibration via pyjnius, `VIBRATE` permission), a short screen shake when the player is hurt, ambience (`Ambience`: looping bed for rain/breeze/cave plus scattered birdsong, crickets or drips), action buttons + d-pad, `game/touch.py` for taps (walk-to, use on arrival, attack adjacent). It saves on pause and resets the game timestep on resume. `build_android.sh` assembles `build_src/` (main.py + sprites.py + sfx.py + particles.py + settings.py + `game/` + `clingine/renderer.py`, never the curses modules) and runs Buildozer with `buildozer.spec` (API 36, AAB). See `docs/ANDROID.md`.

### Map Layout (200×80)

```
Cols 0-49:    Meadow/Forest (grass, trees, paths)
Cols 50-119:  Upper (rows 0-39) = Rocky Hillside (rock, ore)
              Lower (rows 40-79) = River Delta (shallow, bank, deep)
Cols 120-199: Cave Network (cave floor, cave wall, rich ore)
Center (100,40): Town — Shop(S), Lapidary(L), Save(P)
```

### Scene Graph

`state.active_scene` names the current screen; `main.py` hands each frame to `SceneManager.frame()`, which calls `enter()` on a switch, then `update()`, then `render()` (skipped if the update switched away). New screens must be registered in `game/scenes/__init__.py::build_scenes()` (a test checks every name assigned in `game/`).
`menu` → `game` → `map` / `shop` / `lapidary` / `save_point` / `death` / `win` / `daily_end`; `menu` → `perks` / `achievements` / `bestiary` / `stats` / `leaderboard`

### Key Invariants

- **`screen_array` cell:** always `[is_changed: bool, char: str, color_pair: tuple|None]`. Never change this structure.
- **Screen size:** never hard-code it in drawing code: use `renderer.width/height` (the usable area; `CursesRenderer` hides the curses-unsafe last row/col itself) and the `camera.View` from `camera.render_view()`. Simulation code must never depend on the screen: it uses the fixed `VIEW_WIDTH×VIEW_HEIGHT` view (`state.camera_*`, `camera.on_screen`), and the drawn view always lies inside it.
- **Tiles are types:** game code stores/changes tile `type`/`depleted`/`visibility` in `TileMap.meta`; never chars or colors (those come from `theme.py`). `game/` must not import `clingine`.
- **Sprites:** `renderer.set_sprite(x, y, layer, sprite, tint, entity=None)` is per frame (pass a stable `entity` key for things that move, so Kivy glides them between cells) (unset = gone) and a no-op on text renderers; sprite ids are game names (tile type, `depleted`, `player`, `gem`, `bag`, enemy name), never image paths. A new tile type or enemy needs pixel art in `mobile/sprites.py` (a test checks).
- **Color pairs:** always `((r,g,b),(r,g,b))` tuples. Never call `curses.init_pair` directly.
- **Input:** game code never reads raw keys. Update functions take an `InputState` (`game/input.py`) of `Action`s; raw key names appear only in `DEFAULT_KEYMAP`. `main.py` calls `window.keyboard.poll()` then `map_keys()` exactly once per frame.
- **Movement:** one step per move action in `inp.pressed` (or while in `inp.held`, for frontends that report releases), rate-limited by `MOVE_COOLDOWN`; a direction change during the cooldown is queued. Use `inp.pressed` for single-fire actions.
- **Quitting:** scenes set `state.quit_requested`; only the main loop exits.
- **Randomness:** gameplay rolls (drops, polishing, spawns) use `state.rng` (`gameplay_rng(seed)`), never the global `random` module; world generation uses its own `random.Random(seed)`. Render/preview code must not draw from `state.rng`.
- **Time:** game logic uses the fixed step `dt` and `state.game_time` (advances only while the game scene is simulated) — never `time.time()`. Logic goes in `game/simulation.py::step_game`, drawing in `GameScene.render` (`game/scenes/game.py`); state the simulation reads (e.g. the camera) must be updated by the simulation, not by rendering.

## Save Files

Stored in `persistence.data_dir()`: `~/Library/Application Support/GemCollector` (macOS), `%APPDATA%\GemCollector` (Windows), `$XDG_DATA_HOME/gemcollector` (Linux), or `$GEM_COLLECTOR_DATA_DIR` when set (Android, tests). Older `save.json`/`leaderboard.json` next to `main.py` are copied there once at startup.

- `save.json` — single slot, compact JSON with `schema_version` and `worldgen_version`; fog is a run-length string; includes the gameplay RNG state. Old formats are upgraded by `persistence.MIGRATIONS`; a damaged file is moved to `save.json.bak` and the menu shows why.
- **Changing world generation for an existing seed? Bump `world.WORLDGEN_VERSION`** — saved tile coordinates are tied to it (on mismatch the map resets, progress is kept). **Changing the save layout? Bump `SCHEMA_VERSION` and add a migration.**
- `leaderboard.json` — top 10 runs by lifetime earnings; `daily.json` — top 10 daily scores per date.
- `profile.json` — reputation, perks and the ids of runs already rewarded (each run pays out once); written atomically, a damaged file is moved to `profile.json.bak`.
