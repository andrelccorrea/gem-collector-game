# Gem Collector: Improvement and Android Roadmap (2026-10-08)

## 1. Executive summary

- **What the code base looks like.** The game, engine and `main.py` come to about 4.9k lines, and the tests add about 1.5k more. All 124 tests pass. Rendering already has a clean boundary in `clingine/renderer.py:5-21,56-82`, but four things tie the game to the desktop terminal:
  - pynput reads keyboard input for the whole OS.
  - Game logic reads the wall clock with `time.time()`.
  - Sizes are fixed at 80x24 in `game/constants.py:6-11`.
  - Save files use paths relative to the launch folder.
- **Android decision.** Stay in Python and target Kivy with Buildozer/python-for-android, using Python 3.13. Before building the frontend, run a short test build that proves an API 36, 16 KB-compatible build works. If it fails, the fallback is a rewrite in Godot 4.7.
- **Phase 0 is required for every port option.** It covers an input layer that turns keys into game actions, a game clock with a fixed timestep, one seeded random generator, a versioned save format with a per-platform data folder, scene objects, tiles stored as types, and a viewport size read at runtime. Most items are small or medium.
- **Phase 1 fixes measured bugs and slow spots:**
  - `ensure_connectivity` takes about 95% of world generation time (460–970 ms per seed).
  - An idle game frame redraws 1,430 of 1,817 cells.
  - About 55% of enemy spawns are removed the next frame.
  - New Game keeps state from the previous run.
  - The Lapidary price preview changes every frame.
  - A failed save still says "Game Saved!".
  - Quick key taps are lost.
- **Phase 2 adds tension to each trip out of town and features that bring players back on mobile.** In order: gem drops that depend on the tool, a bag-size limit, a lantern that burns down, cut-quality tiers at the Lapidary, shop prices that drop when you sell too much of one gem, progress kept between runs, and a daily seeded run. All of them work on a touch screen.

---

## 2. Recommended Android path

**Recommendation: keep a pure-Python game core, use Kivy with Buildozer/python-for-android for Android, and pin Python 3.13.**

| Option | Status (verified) | Verdict |
|---|---|---|
| **Kivy 2.3.1 + python-for-android 2026.5.9 + Buildozer 1.6.0** | Kivy supports Python 3.8–3.13 and Kivy 3.0 is still in development. python-for-android added an SDL3 bootstrap in May 2026 and has built AAB files since v2022.03.13. Buildozer has a minimum API of 24. **Not confirmed:** python-for-android's default target API; its tests target API 35, and nothing mentions 16 KB pages. | **Chosen.** It is the only Python route with a working Android packaging chain for an SDL-based app. https://github.com/kivy/kivy/releases ; https://github.com/kivy/python-for-android/releases ; https://github.com/kivy/buildozer/releases |
| python-tcod 21.2.1 (SDL3) | Its console model (a character plus foreground and background color per cell) matches `screen_array` almost one to one. It has cp314 wheels. python-for-android has **no tcod recipe**. It has 168 recipes, including sdl3 3.4.2, sdl3_mixer 3.2.0, numpy and cffi. | Optional for the desktop and terminal later. **Keep it out of `game/`** until a tcod recipe for python-for-android exists. https://pypi.org/project/tcod/21.2.1/ |
| pygame-ce 2.5.8 / pygbag 0.9.3 | No official Android support. python-for-android's "pygame" recipe builds the original pygame 2.1.0, not pygame-ce. Issue #3265: the APK builds but **fails at runtime when the app starts** (`pygame._freetype`). pygbag runs on CPython 3.11, with 3.12 as its "next" build. | Only useful for a web build on itch.io. It is not on the Android path. https://github.com/pygame-community/pygame-ce/issues/3265 |
| BeeWare Briefcase / Flet 1.0.3 | Briefcase targets API 36 but cannot deploy pygame on Android. Flet 1.0.0 (Sep 14, 2026) builds AAB files and bundles CPython 3.14, but it is an app UI framework. | Not suited to a 30 FPS tile game. |
| Godot 4.7.2 (rewrite) | Godot builds AAB files and handles touch input natively. The official 4.7 export docs list only SDK Platform 35. **API 36 as the default target is claimed only on the community forum.** A rewrite means porting about 4.9k lines of code plus about 1.5k lines of tests. | **Fallback** if the Kivy test build fails. https://docs.godotengine.org/en/4.7/tutorials/export/exporting_for_android.html |

**Google Play rules (confirmed):**
- New apps and updates must target **API 36** since Aug 31, 2026. An extension to Nov 1, 2026 can be requested. https://developer.android.com/google/play/requirements/target-sdk
- Apps that target API 35 or higher and include native code must support **16 KB memory pages**. From Feb 1, 2027, updates that don't will be blocked. Chaquopy recommends Python 3.13 or later for 16 KB support. https://developer.android.com/guide/practices/page-sizes
- Re-check both pages when Phase 3 starts.

**What this decision means now:**
1. **Code in `game/` must stay compatible with Python 3.13.** Development runs on 3.14 (`.python-version`), but Kivy 2.3.1 stops at 3.13. CI should run both 3.13 and 3.14.
2. **`game/` uses only the standard library.** No numpy and no tcod in the core. Pathfinding and field of view stay in pure Python.
3. **Only `clingine/` may import curses or anything platform-specific.** Today `game/world.py:5` is the only game module that imports clingine. Keep it that way, then remove it in item 0.7.
4. **The second frontend is the Kivy desktop build,** not a throwaway pygame frontend, because the Kivy code is what ships to Android. It needs a separate 3.13 virtual environment.

---

## 3. Phased roadmap

### Phase 0: Foundations that unblock the port

| # | What | Why | Evidence | Effort |
|---|---|---|---|---|
| 0.1 | **Project setup.** Add `.gitignore` (save.json, leaderboard.json, `__pycache__`, .DS_Store) and `pyproject.toml` with ruff and pytest settings. Add GitHub Actions running uv, `ruff check`, `ruff format --check` and pytest on 3.13 and 3.14. Reformat the tab-indented files in a separate commit. Delete about 880 lines of unused, broken engine code: `shapes.py` (725), `sprite.py` (87), `label.py` (69), the `map_loader.py` stub, the `Window.run` stub and `Mouse.get_clicked`. | The repo has no commits and no ignore file. The dead code calls `draw_line(self.window,…)`, but `Window` has no `get_cell` or `set_cell`. | `setup.cfg:1-7`; `requirements.txt:1-3`; `clingine/__init__.py:1-13`; `clingine/shapes.py:45-49`; `clingine/util.py:123-133` | S |
| 0.2 | **Input layer and removal of pynput.** Add an `Action` enum and an `InputState` (`pressed`/`held`) passed to update functions in place of `window`. Read keys with curses `getch()`, and treat a key as held while key-repeat keeps firing. Remove `pynput`, `python-xlib` and `six`. | pynput doesn't exist on Android. It captures keys system-wide (Esc in another app quits the game) and needs Accessibility permission on macOS. This item also fixes the lost-tap bug and the unlocked cross-thread key sets. It is the foundation for touch input. | `clingine/keyboard.py:1,9-10,17,22-35`; `clingine/window.py:24-25,69`; `game/player.py:56-65`; `game/combat.py:9`; `game/tools.py:24,42`; `game/buildings.py:27,292-324,555-575,648-650`; `game/menu.py:65-78`; https://pynput.readthedocs.io/en/latest/limitations.html | M |
| 0.3 | **Game clock and fixed timestep.** Add a `state.game_time` that advances only in the game scene. Run updates in fixed steps from an accumulator using `perf_counter`, with dt capped at 0.25 s. Sleep `max(0, target - elapsed)`. | Cooldowns and regen use `time.time()`, so they keep running in menus and while an Android app is suspended. dt leaves out the frame's work, so game time runs slower than real time and the real FPS is below 30. | `clingine/clock.py:10-17`; `clingine/window.py:90-91`; `main.py:34`; `game/player.py:98`; `game/combat.py:29,93`; `game/state.py:47`; https://gafferongames.com/post/fix_your_timestep/ | S |
| 0.4 | **One seeded random generator.** Put `state.rng` (`random.Random`, seeded from `state.seed`) on GameState and pass it to `roll_gem_drop`, the polish roll and `spawn_enemies`. | Runs can't be reproduced today, and tests work around it with `random.seed(42)`. The balance simulation and the daily run need this. | `game/gems.py:23,52`; `game/enemies.py:88,116-117`; `game/menu.py:86-90`; `tests/test_gems.py:100` | S |
| 0.5 | **Save format v1.** Write `schema_version` and `worldgen_version` and add a `migrate()` chain. Put saves in a `data_dir()` (platformdirs on desktop, the app folder on Android). Have the menu use `has_save()`. Make `save_game` return success or an error and show it in the HUD. Back up an unreadable file to `.bak`. Store fog as a bitset or run-length string, without `indent`. | Changing `world.py` or the gem catalog silently moves depleted and fog coordinates onto the wrong tiles. A fully explored save is 806 KB. A failed save still shows "Game Saved!". | `game/persistence.py:7-8,17-56,64-68,76-78`; `game/menu.py:44,64,115-120`; `game/buildings.py:653-654`; `game/objects/registry.py:12-20`; `game/world.py:247-264` | M |
| 0.6 | **Scenes.** Add a Scene protocol (`handle(input)`, `update(dt)`, `render(renderer)`) and a stack-based SceneManager. Menu Esc sets `state.quit_requested` instead of calling `window.exit()`. Split `buildings.py` into `game/scenes/{shop,lapidary,save_point}.py` with a shared scrolling `ListMenu`. | The Android back button then simply closes the top screen. This removes the if/elif chain on scene names and the imports inside the loop. The shared list fixes "Sell All" being drawn off-screen. | `main.py:37-80,71-122`; `game/menu.py:77-78`; `game/buildings.py:267-278,530-541,384-388,423-427` | M |
| 0.7 | **Tiles stored as types, with a theme layer.** Surface stores a tile-type id. Each frontend's theme chooses the character and color (or sprite). Move fog dimming out of `Surface.blit`. | Kivy needs to look up a sprite from the tile type. Afterwards, `game/` no longer imports clingine. | `game/world.py:5,69-70`; `clingine/surface.py:11-19,67-77`; `game/camera.py:46-56` | M |
| 0.8 | **Viewport size read at runtime.** Take the viewport and HUD sizes from `renderer.width/height`. Keep the rule against writing the last row and column inside CursesRenderer only. | Phones vary in size and orientation. The 78-column width exists only because of that curses rule. | `game/constants.py:6-11`; `game/camera.py:7-10,39`; `game/hud.py:14-22`; `game/enemies.py:98,278-279`; `clingine/renderer.py:37-39` | M |

### Phase 1: Quick wins (speed, bugs, quality)

| # | What | Why | Evidence | Effort |
|---|---|---|---|---|
| 1.1 | **Rewrite `ensure_connectivity`.** Label connected regions once, then join them with one BFS that starts from every reachable tile at once. Bump `worldgen_version` (this depends on 0.5). | It takes 2.03 s of 2.14 s for seed 7 (6.9M generator calls in the nested `min()`). Loading a save spends about 746 ms regenerating the world. The target is under 50 ms. | `game/world.py:486-505` | M |
| 1.2 | **Faster test suite.** Share one generated world across tests (session-scoped fixture). | The 22 `generate_world` calls dominate the 17–19 s run. The target is under 2 s. | `tests/test_world.py:23-29`; `tests/test_fog.py:8` | S |
| 1.3 | **Make partial redraw work.** Compare before calling `set_cell` for fog "unseen" cells, the HUD and menus. Don't call `clear()` every frame. Fix the None-to-`window.color_pair` substitution. | An idle game frame marks 1,430 of 1,817 cells as changed. A menu frame marks all 1,817. | `clingine/surface.py:67-70`; `game/hud.py:20-22`; `clingine/renderer.py:46-53`; `game/menu.py:26-33`; `clingine/window.py:68-87` | M |
| 1.4 | **Colors.** Map RGB to the nearest of the 256 xterm colors without calling `init_color`. Check `can_change_color()` once. Replace the bare `except` with `except curses.error`. | Color numbers wrap around and overwrite each other. Terminal.app falls back to monochrome. The game changes the user's terminal palette. The check runs for every changed cell. | `clingine/util.py:11-17,30-39,60-89`; `clingine/window.py:75-87` | M |
| 1.5 | **New Game resets fully.** Start from a fresh `GameState()` and remove the duplicated reset code (or use `init_player`). | Enemies, `lapidary_level`, `polished_gem_values` and the cursors carry over after death. | `game/menu.py:85-112`; `game/player.py:21-39` | S |
| 1.6 | **Spawn enemies in a ring around the player,** outside the viewport and inside `ENEMY_MAX_DISTANCE`. | 1,095 of 2,000 spawns are removed the next frame, so the real spawn rate is about half of `DIFFICULTY_TIERS`. | `game/enemies.py:115-117` vs `:214-217` | S |
| 1.7 | **Lapidary prices.** Store one price per polished item. Show a min–max range in the preview. Use `mult_max`. | The preview changes every frame. Each new cut re-prices every polished gem of that type already held. | `game/buildings.py:455,602-603`; `game/gems.py:50-53`; `game/constants.py:159-165` | S |
| 1.8 | **One `biome_at(x,y)` and one `is_town(x,y)`.** | The biome lookup is written four times, and the town size differs everywhere (±6/±4, ±8/±6, ±7/±5). The HUD can show "Town" where HP regen doesn't work. | `game/hud.py:71-84`; `game/enemies.py:66-73,91-92`; `game/tools.py:153-161`; `game/player.py:107-108`; `game/world.py:43-63,581-588` | S |
| 1.9 | **Pathfinding.** Store parent pointers instead of copying the path. Give each enemy a random starting `path_timer`. Treat the town as blocked. Don't walk through walls when falling back. This is reused by tap-to-move in 3.3. | Copying the path costs quadratic time and memory. All path recalculations land on the same frame. The greedy fallback ignores walls and gets enemies stuck. | `game/enemies.py:42,160-201,231-239,256` | S |
| 1.10 | **Tests for the untested gameplay code:** buildings, combat, enemies, tools, player, menu reset, and a full save-then-load round trip. | These are the main gameplay modules and have no tests. They are the safety net for 0.6 and 0.7. | `tests/` (no files for these modules) | M |
| 1.11 | **Gem, tool and enemy definitions in one `catalogs.toml`** (read with stdlib `tomllib`), keeping the dataclasses. | It gives a fixed catalog order (the order from pkgutil feeds `rng.choices` in world generation) and removes module discovery that would have to work inside an Android bundle. | `game/objects/registry.py:10-21` | S |
| 1.12 | **Remove unused constants, fields and branches. Add a player attack cooldown.** | Dead code. Whether held F floods attacks through key auto-repeat is **not verified**, but a cooldown is cheap either way. | `game/constants.py:19,45,52,81,150-156`; `game/state.py:50,60`; `game/combat.py:7-29` | S |

### Phase 2: Gameplay ideas, ranked by fun versus effort

Before this phase, build a **headless economy simulation** (M). It runs N seeded bots with the StubRenderer and reports minutes to $10k and gold per minute for each biome. It needs 0.3 and 0.4, and every item below is tuned with it. Evidence: `clingine/renderer.py:56`; `game/constants.py:169`.

| Rank | What | Why (gap it fills) | Evidence | Effort | Mobile fit |
|---|---|---|---|---|---|
| 1 | **Gem drops depend on the tool tier** (SteamWorld/Core Keeper ore gating) | `tool_name` is never used, so a basic shovel finds diamonds as often as an upgraded pickaxe | `game/gems.py:13-24` | S | Neutral |
| 2 | **Bag capacity plus cargo upgrades** (SteamWorld Dig, Motherload) | Inventory is unlimited, so there is no reason to head back to town | `game/gems.py:27` | S | Excellent |
| 3 | **Death drops the bag where you died; reviving costs a fee** ("Normal" mode, with the current rule kept as "Hardcore") | Death is a hard stop. Phone players dislike losing long sessions | `game/combat.py:95-98`; `game/player.py:119-122` | S | High |
| 4 | **Remove the loot-farming loop** (the DCSS rule against grinding) | Enemies respawn without limit and their loot always sells | `game/buildings.py:196-208,395-431` | S | Neutral |
| 5 | **Daily seeded run** with seed = hash(date), a time limit and its own leaderboard (Spelunky) | The world is already generated from a seed. Needs 0.4 and 0.5 | `game/persistence.py:154-173` | S | Excellent |
| 6 | **Lantern fuel shrinks the fog radius,** draining faster in Cave and River Delta (no death when it runs out) | The fog radius is a fixed 8, so going deep into the caves costs nothing | `game/constants.py:13`; `game/fog.py:14-23` | M | High |
| 7 | **Lapidary cut-quality tiers plus a timing minigame** (Dwarf Fortress) | Polishing is a flat random roll. This becomes the game's signature system. Needs 1.7 | `game/gems.py:45-55` | M | Excellent (tap timing) |
| 8 | **Shop prices fall as you sell the same gem, and recover over time** (Moonlighter) | Prices are fixed, so dumping one gem type is the best strategy | `game/buildings.py:358-393` | M | Excellent |
| 9 | **Progress kept between runs** ("Prospector Reputation" perks and challenge contracts) | No reward survives death. The leaderboard is only written on a win | `game/menu.py:138-160` | M | Excellent |
| 10 | **Rough gems appraised at the Lapidary** (Brogue identification, Stardew geodes) | Adds discovery to every dig and a gold sink | `game/tools.py:108-136` | S | High |
| 11 | **Staged shop stock** unlocking at $2.5k, $5k and $7.5k (Super Motherload) | Everything is for sale from the start, so there are no mid-game goals | `game/buildings.py:51-80`; `game/constants.py:169-174` | S | High |
| 12 | **Line-of-sight fog** (shadowcasting in pure Python, keeping the stdlib-only rule) | You can see through cave walls today | `game/fog.py:14-23` | M | Neutral |
| 13 | **Fast-travel waypoints or recall items** | Town (100,40) is the only hub, and the caves run to x=199 | `game/constants.py` (TOWN_CENTER, BIOME_CAVE_MIN_X) | M | High |
| 14 | Tool mod slots with free reassignment / a trophy-gem museum / generated "legendary lode" lore | Gives gems a use besides selling, plus collection goals | `game/data/catalogs.toml` ([tool_upgrades]); `game/world.py` | M/S/M | High |
| Deferred | Dome Keeper-style raids on Town (L); idle income from hired miners (it undermines the $10k race) | — | `game/constants.py:24,169-174` | L/M | Medium |

### Phase 3: Port

| # | What | Why | Evidence | Effort |
|---|---|---|---|---|
| 3.1 | **Go/no-go test build.** Build a Kivy "hello grid" app with Buildozer, `android.api=36`, Python 3.13 and an AAB. Check `targetSdkVersion` in the merged manifest and 16 KB alignment of every `.so` file. If it fails, choose Godot 4.7 and confirm the target SDK in its export preset. | python-for-android's default API 36 is unconfirmed (its tests use 35). Godot's API 36 claim is forum-only. | python-for-android releases; https://developer.android.com/guide/practices/page-sizes | M |
| 3.2 | **Kivy frontend:** KivyRenderer (glyph or sprite grid from the 0.7 theme) and KivyInput producing the same `InputState`. Prove it on the desktop first. | A frontend works by swapping the renderer and input classes once Phase 0 is done | `clingine/renderer.py:5-21` | L |
| 3.3 | **Touch controls:** tap-to-move using the pathfinding from 1.9. Tapping an adjacent enemy attacks it and tapping a resource tile mines it. One context-sensitive action button replaces Space and F, plus an optional d-pad. Touch targets of at least 48dp with 8dp spacing. Confirm before risky actions. Portrait layout. | The game relies on held keys today. Mis-taps are Shattered Pixel Dungeon's main complaint | `game/enemies.py:153`; https://support.google.com/accessibility/android/answer/7101858 | M |
| 3.4 | **Android lifecycle:** on pause, save and stop the game clock. The back button closes the top scene. On-screen hints come from the active input's action table. | Needs 0.3 and 0.6. Hard-coded hints are wrong on touch | `game/hud.py:43`; `game/menu.py:59`; `game/buildings.py:281` | S |
| 3.5 | **Play Store release:** AAB, API 36 (re-check the requirement), 16 KB pages, and data-safety answers (the opt-in local telemetry log only) | Compliance | https://developer.android.com/google/play/requirements/target-sdk | M |

---

## 4. First concrete task: item 0.2, the input layer and removing pynput

**Why this first:** it is the largest blocker for the port and fixes two confirmed bugs (lost taps, system-wide key capture). It also creates the slot where touch input will plug in later. Before starting, the user should make a baseline commit of the current tree, since the repo has no commits yet.

**Acceptance criteria:**
1. `game/input.py` defines an `Action` enum (MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, USE, ATTACK, CYCLE_TOOL, CONFIRM, CANCEL), an `InputState` (`pressed: frozenset[Action]`, `held: frozenset[Action]`) and one `DEFAULT_KEYMAP`.
2. Every update function in `game/` (player, combat, tools, buildings, menu) and in `main.py` reads input only from `InputState`. Running `grep -rnE "keyboard\.|\"space\"|\"esc\"|\"enter\"" game/ main.py` finds matches only in `DEFAULT_KEYMAP`.
3. A curses input backend in `clingine/` reads every pending `getch()` once per frame and fills `InputState`. Terminals send no key-release, so a time-window "held" either stutters (shorter than the OS initial repeat delay) or overshoots after release (longer). *Implemented instead:* each press/auto-repeat is one step, rate-limited by `MOVE_COOLDOWN`, with a direction change during the cooldown queued; `InputState.held` is reserved for frontends that report releases (touch). The one-step pause before OS auto-repeat starts is inherent to terminals (the kitty keyboard protocol could remove it later). `Window.update` no longer calls `getch()` and throws the result away (`clingine/window.py:69`).
4. A key pressed and released within one frame appears in `pressed` for exactly one frame. A unit test covers this.
5. `pynput`, `python-xlib` and `six` are removed from `requirements.txt`. `clingine/keyboard.py` is deleted.
6. Tests build `InputState` directly, with no fake window for input. All existing tests plus the new mapping and tap tests pass.
7. Manual check in macOS Terminal.app: the game runs **without** Accessibility or Input Monitoring permission. Typing in another window has no effect on the game. Holding an arrow key moves the player smoothly, and Space, E, F, Esc and Enter each fire exactly once per press.

I can go deeper on any phase, for example an interface sketch for 0.2 or 0.6, or a plan for the 3.1 test build.