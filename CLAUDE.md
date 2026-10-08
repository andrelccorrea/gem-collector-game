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

Requires a 256-color terminal at ≥80×24. The game renders at 80×24 with an 80×20 viewport and 2-row HUD.

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move |
| Space | Use tool / interact with building |
| E | Cycle equipped tool |
| F | Attack nearest enemy |
| Esc | Open menu / close sub-screen |
| Enter | Confirm selection |

## Architecture

### Engine (`clingine/`)

**`window.py`** — Central coordinator. Calls `curses.initscr()`, manages `screen_array[y][x] = [is_changed, char, color_pair]`, flushes only dirty cells via `window.update()`. Color pairs are lazy-allocated via `window.color_pairs.get_color_pair(((r,g,b),(r,g,b)))`.

**`surface.py`** — Off-screen tile buffer. `Surface(width, height)` with `set_tile(x, y, char, cp)`, `get_tile(x, y)`, `fill()`, and `blit(window, cam_x, cam_y, vp_w, vp_h, dest_y)` which copies a viewport slice into `screen_array` respecting dirty flags. Game code attaches a `surface.meta` dict: `(x,y) -> {"type", "walkable", "interactable", "depleted"}`.

**`keyboard.py`** — reads keys via curses `getch()` (no OS hooks or permissions). `poll()` drains pending events once per frame into `pressed` (lowercase key names that fired this frame: new press or OS auto-repeat). Terminals never report releases, so holding a key is a stream of presses; there is no held set.

**`util.py`** — `ColorPairs`, `Colors`, `Image`, `load_image`, `load_images`, plus module-level `draw_line(window, x1, x2, y, char, cp)` and `draw_endpoints(...)`.

**`clock.py`** — `Clock.tick(fps)` sleeps until the next fixed frame deadline (overshoot does not accumulate) and returns the full frame duration.

### Game (`game/`)

| Module | Role |
|--------|------|
| `constants.py` | All magic numbers: MAP_WIDTH=200, MAP_HEIGHT=80, VIEWPORT=78×20, FPS=30, biome colors, gem catalog, tool catalog, enemy catalog, difficulty tiers |
| `state.py` | `GameState` dataclass — single source of truth for player, world, enemies, inventory, scene |
| `simulation.py` | `new_run(seed)` (fresh GameState: world, player, fog, camera) and `step_game(inp, state, dt)` (one fixed simulation step, no drawing) — same seed + same inputs = same run |
| `loop.py` | `FixedTimestep`: turns frame time into fixed 1/FPS simulation steps (clamped at 0.25 s), buffering pressed input until a step consumes it; `reset()` freezes time outside the game scene |
| `input.py` | `Action` enum, `InputState` (`pressed`/`held` actions), `DEFAULT_KEYMAP`, `map_keys()` — the frontend-agnostic input boundary |
| `world.py` | `generate_world(seed)` → 200×80 `Surface` with biomes + town. `ensure_connectivity()` BFS flood-fill. |
| `camera.py` | `update_camera(state)` centers on player clamped to map. `render_viewport(window, state)` blits tile slice. |
| `hud.py` | `render_hud(window, state)` writes to rows 20-21: HP (color-coded), Gold, Tool, Biome, key hints, HUD messages |
| `player.py` | `init_player`, `update_player` (movement via held move actions, HP regen in town, death check), `render_player`, `set_hud_message` |
| `tools.py` | E-key cycles tools; Space-key mines tiles, depletes them, rolls gem drops |
| `gems.py` | `roll_gem_drop(biome, tool, rng)` weighted random; `add_gem_to_inventory`; polished gem value computation |
| `enemies.py` | `Enemy` class; BFS pathfinding (cap 50 steps); `spawn_enemies`, `update_enemies`, `render_enemies`; difficulty scaling |
| `combat.py` | F-key player attack (Chebyshev-1 adjacency); enemy auto-attacks on per-enemy cooldown |
| `buildings.py` | Shop (buy/upgrade tools, sell gems/loot), Lapidary (cut gems, upgrade machine), Save point |
| `persistence.py` | `save_game` (atomic, returns an error message or None), `load_game` (migrates, regenerates world from seed, re-applies depleted tiles/fog; raises `SaveLoadError`), `data_dir()`, leaderboard |
| `menu.py` | Main menu, death screen, win/Hall of Fame screen, leaderboard display |

### Map Layout (200×80)

```
Cols 0-49:    Meadow/Forest (grass, trees, paths)
Cols 50-119:  Upper (rows 0-39) = Rocky Hillside (rock, ore)
              Lower (rows 40-79) = River Delta (shallow, bank, deep)
Cols 120-199: Cave Network (cave floor, cave wall, rich ore)
Center (100,40): Town — Shop(S), Lapidary(L), Save(P)
```

### Scene Graph

`state.active_scene` controls the main loop dispatcher:
`menu` → `game` → `shop` / `lapidary` / `save_point` / `death` / `win` / `leaderboard`

### Key Invariants

- **`screen_array` cell:** always `[is_changed: bool, char: str, color_pair: tuple|None]`. Never change this structure.
- **Boundary guard:** never write to `window.height-1` row or `window.width-1` col.
- **Color pairs:** always `((r,g,b),(r,g,b))` tuples. Never call `curses.init_pair` directly.
- **Input:** game code never reads raw keys. Update functions take an `InputState` (`game/input.py`) of `Action`s; raw key names appear only in `DEFAULT_KEYMAP`. `main.py` calls `window.keyboard.poll()` then `map_keys()` exactly once per frame.
- **Movement:** one step per move action in `inp.pressed` (or while in `inp.held`, for frontends that report releases), rate-limited by `MOVE_COOLDOWN`; a direction change during the cooldown is queued. Use `inp.pressed` for single-fire actions.
- **Quitting:** scenes set `state.quit_requested`; only the main loop exits.
- **Randomness:** gameplay rolls (drops, polishing, spawns) use `state.rng` (`gameplay_rng(seed)`), never the global `random` module; world generation uses its own `random.Random(seed)`. Render/preview code must not draw from `state.rng`.
- **Time:** game logic uses the fixed step `dt` and `state.game_time` (advances only while the game scene is simulated) — never `time.time()`. Logic goes in `game/simulation.py::step_game`, drawing in `main.py::_render_game`; state the simulation reads (e.g. the camera) must be updated by the simulation, not by rendering.

## Save Files

Stored in `persistence.data_dir()`: `~/Library/Application Support/GemCollector` (macOS), `%APPDATA%\GemCollector` (Windows), `$XDG_DATA_HOME/gemcollector` (Linux), or `$GEM_COLLECTOR_DATA_DIR` when set (Android, tests). Older `save.json`/`leaderboard.json` next to `main.py` are copied there once at startup.

- `save.json` — single slot, compact JSON with `schema_version` and `worldgen_version`; fog is a run-length string; includes the gameplay RNG state. Old formats are upgraded by `persistence.MIGRATIONS`; a damaged file is moved to `save.json.bak` and the menu shows why.
- **Changing world generation for an existing seed? Bump `world.WORLDGEN_VERSION`** — saved tile coordinates are tied to it (on mismatch the map resets, progress is kept). **Changing the save layout? Bump `SCHEMA_VERSION` and add a migration.**
- `leaderboard.json` — top 10 runs by lifetime earnings.
