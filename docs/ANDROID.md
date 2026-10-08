# Android build and release

The Android app is the Kivy frontend in `mobile/main.py` running the same `game/`
package as the terminal version. Everything except the Android toolchain is ready and
tested on the desktop; the steps below need your machine, your licence acceptance and
(for the Play Store) your developer account.

## 1. Run the mobile frontend on the desktop

```bash
uv venv -p 3.13 .venv-mobile            # Kivy 2.3.1 supports Python up to 3.13
VIRTUAL_ENV=.venv-mobile uv pip install "kivy==2.3.1"
.venv-mobile/bin/python mobile/main.py
```

Mouse clicks act as taps; the keyboard also works (same keys as the terminal game).

## 2. Toolchain (one time)

```bash
brew install openjdk@17                  # Buildozer/Gradle need JDK 17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
python3 -m pip install --user "buildozer==1.6.0" cython
```

The first build downloads the Android SDK, NDK and python-for-android (several GB).
**You must accept the Android SDK License Agreement**: either answer the prompts during
the first build, or, after reading it, set `android.accept_sdk_license = True` in
`mobile/buildozer.spec`.

## 3. Go/no-go test build (roadmap 3.1)

```bash
cd mobile
./build_android.sh                       # debug APK in mobile/bin/
adb install -r bin/*.apk                 # phone with USB debugging enabled
```

Check before investing further:

- [ ] The merged manifest targets API 36:
      `aapt dump badging bin/*.apk | grep targetSdkVersion` → `36`.
- [ ] Every native library is 16 KB-aligned (required for API 35+ apps with native code
      from 2026 on): `zipalign -c -P 16 -v 4 bin/*.apk` reports no failures.
- [ ] The app starts on a real device and reaches the menu.

If either platform check fails with the current Buildozer/python-for-android, the
fallback recorded in `docs/ROADMAP.md` is a Godot 4 rewrite of the frontend.

## 4. On-device test checklist

- [ ] Menu: d-pad ^/v moves, OK selects, Back quits (and the Android back button = Back).
- [ ] Tap a far tile: the player walks there around obstacles; tap a dig spot or gem: it
      walks there and digs/picks it up; tap an adjacent enemy: attacks.
- [ ] Shop, Lapidary (cutting minigame: OK stops the marker), Save point, Museum, Perks.
- [ ] Press Home during a run, wait, return: no time passed in the game; kill the app
      from recents and reopen: Continue resumes (the run was saved on pause).
- [ ] Daily Run shows the timer and is not saved on pause.
- [ ] Text is readable and buttons are easy to hit (≥ 48 dp) on a small phone.

## 5. Release (Play Store)

```bash
cd mobile
./build_android.sh android release       # AAB in mobile/bin/
```

- Create an upload keystore (`keytool -genkey -v -keystore upload.jks -alias upload
  -keyalg RSA -keysize 2048 -validity 10000`) and point Buildozer at it
  (`P4A_RELEASE_KEYSTORE`, `P4A_RELEASE_KEYSTORE_PASSWD`, `P4A_RELEASE_KEYALIAS`,
  `P4A_RELEASE_KEYALIAS_PASSWD`). Keep it out of the repository.
- Set a real `package.domain` in `buildozer.spec` before the first upload — the app id
  cannot change afterwards.
- Play Console: the app collects no data (saves, scores and the profile stay on the
  device), so the Data safety form is "no data collected / no data shared".
- Re-check the target-API and 16 KB requirements on the Android developer site right
  before submitting; both change over time.

## Design notes

- **Landscape:** the game draws an 80x24 character grid (the terminal layout) next to a
  control panel. Portrait would need a narrower layout for menus and the shop; that is a
  possible follow-up once the game is playable on devices.
- **Saves** go to the app's private storage (`App.user_data_dir`, via
  `GEM_COLLECTOR_DATA_DIR`).
- **Determinism:** the simulation never depends on the screen size; the drawn view is
  capped at the 79x21 simulation view (`docs/BALANCE.md` and the replay tests rely on it).
