[app]
title = Gem Collector
package.name = gemcollector
# Change to a domain you control before publishing (it becomes the app id).
package.domain = dev.gemcollector
# build_android.sh assembles this folder: main.py + the game package + the renderer.
source.dir = build_src
source.include_exts = py,toml
version = 0.1.0
requirements = python3,kivy==2.3.1
# The 80x24 character grid plus the control panel need a wide screen.
orientation = landscape
fullscreen = 1

# Google Play requires targeting API 36 for new apps and updates (from 2026-08-31).
android.api = 36
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.release_artifact = aab
android.debug_artifact = apk
# Building downloads the Android SDK/NDK; their licenses must be accepted by you.
# Leave this False to review and accept them interactively, or set True if you have
# read and accept the Android SDK License Agreement.
android.accept_sdk_license = False

[buildozer]
log_level = 2
warn_on_root = 1
