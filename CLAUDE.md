# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Gem Collector** — a terminal-based gem prospecting RPG built on **clingine**, a custom CLI engine using Python's `curses` library. The player mines gems, fights enemies, visits shops, and races to $10,000 in lifetime earnings.

## Setup & Running

```bash
# Activate virtual environment (Python 3.14)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

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

**`window.py`** — Central coordinator. Calls `curses.initscr()`, manages `screen_array[y][x] = [is_changed, char, color_pair]`, flushes only dirty cells via `window.update(fps)`. Color pairs are lazy-allocated via `window.color_pairs.get_color_pair(((r,g,b),(r,g,b)))`.

**`surface.py`** — Off-screen tile buffer. `Surface(width, height)` with `set_tile(x, y, char, cp)`, `get_tile(x, y)`, `fill()`, and `blit(window, cam_x, cam_y, vp_w, vp_h, dest_y)` which copies a viewport slice into `screen_array` respecting dirty flags. Game code attaches a `surface.meta` dict: `(x,y) -> {"type", "walkable", "interactable", "depleted"}`.

**`keyboard.py`** — pynput listener with three sets:
- `pressed` — keys fired this frame (cleared by `clear_events()`)
- `released` — keys released this frame (cleared by `clear_events()`)
- `held` — keys physically down right now (NOT cleared by `clear_events()`)
- Call `window.keyboard.clear_events()` once per frame; `update()` does NOT do it automatically.

**`util.py`** — `ColorPairs`, `Colors`, `Image`, `load_image`, `load_images`, plus module-level `draw_line(window, x1, x2, y, char, cp)` and `draw_endpoints(...)`.

**`clock.py`** — `get_dt()` returns seconds since last frame; `delay(sec)` caps FPS.

### Game (`game/`)

| Module | Role |
|--------|------|
| `constants.py` | All magic numbers: MAP_WIDTH=200, MAP_HEIGHT=80, VIEWPORT=78×20, FPS=30, biome colors, gem catalog, tool catalog, enemy catalog, difficulty tiers |
| `state.py` | `GameState` dataclass — single source of truth for player, world, enemies, inventory, scene |
| `world.py` | `generate_world(seed)` → 200×80 `Surface` with biomes + town. `ensure_connectivity()` BFS flood-fill. |
| `camera.py` | `update_camera(state)` centers on player clamped to map. `render_viewport(window, state)` blits tile slice. |
| `hud.py` | `render_hud(window, state)` writes to rows 20-21: HP (color-coded), Gold, Tool, Biome, key hints, HUD messages |
| `player.py` | `init_player`, `update_player` (movement via `keyboard.held`, HP regen in town, death check), `render_player`, `set_hud_message` |
| `tools.py` | E-key cycles tools; Space-key mines tiles, depletes them, rolls gem drops |
| `gems.py` | `roll_gem_drop(biome, tool)` weighted random; `add_gem_to_inventory`; polished gem value computation |
| `enemies.py` | `Enemy` class; BFS pathfinding (cap 50 steps); `spawn_enemies`, `update_enemies`, `render_enemies`; difficulty scaling |
| `combat.py` | F-key player attack (Chebyshev-1 adjacency); enemy auto-attacks on per-enemy cooldown |
| `buildings.py` | Shop (buy/upgrade tools, sell gems/loot), Lapidary (cut gems, upgrade machine), Save point |
| `persistence.py` | `save_game` (atomic JSON via tmp+rename), `load_game` (re-generates world from seed, re-applies depleted tiles), leaderboard |
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
- **Key names:** `"up"`, `"down"`, `"left"`, `"right"`, `"space"`, `"esc"`, `"enter"`, `"e"`, `"f"`, `"w"`, `"a"`, `"s"`, `"d"` (lowercase, as returned by pynput).
- **Movement:** use `keyboard.held` for smooth held-key movement; use `keyboard.pressed` for single-fire actions.
- **`clear_events()`:** clears `pressed` and `released` but NOT `held`. Must be called exactly once per frame by the game loop.

## Save Files

- `save.json` — single save slot (gitignore this)
- `leaderboard.json` — top 10 runs by lifetime earnings (gitignore this)
