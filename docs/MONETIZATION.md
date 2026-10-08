# Gem Collector: Monetization Options (2026-10-08)

Research notes for a later decision. Nothing here is implemented yet. Sources are vendor
blogs and project pages, so treat the numbers as rough.

## What the market does

| Model | What it is | Fit for this game |
|---|---|---|
| **Free + supporter pack** | The whole game is free with no ads. One optional purchase unlocks cosmetic extras. This is how *Shattered Pixel Dungeon* works: it is free and open source (GPLv3), and its developer earns money from a supporter purchase, a pay-what-you-want APK, a paid iOS version ($5), GOG and Patreon. ([Flathub](https://flathub.org/id/apps/com.shatteredpixel.shatteredpixeldungeon), [itch.io](https://shattered-pixel.itch.io/shattered-pixel-dungeon/purchase), [iOS post](https://shatteredpixel.com/blog/shattered-pixel-dungeon-is-coming-to-ios.html)) | **Best fit.** It is the closest genre match, it keeps the game fair, and it suits an open-source repo. |
| **Premium** | You pay once and get no ads and no purchases. One guide says it still works for niche games but makes it harder to attract new players. ([Wayline](https://www.wayline.io/blog/mobile-game-pricing-models-monetization-practices), [Bravebits](https://bravebitsglobal.com/blog/complete-guide-mobile-game-monetization-2026)) | Good on iOS or itch.io. On Android it competes with our own free APK, since the repo is public. |
| **Hybrid: ads + purchases** | Most guides call this the default today. Rewarded ads work best because the player chooses to watch one in exchange for a reward. ([Wayline](https://www.wayline.io/blog/mobile-game-monetization-trends-maximize-revenue), [Hitem3D](https://blog.hitem3d.ai/blog/Game-Monetization-Strategies-How-to-Make-Money-from-Your-Game-in-2026)) | Possible later, for example "watch an ad to revive without the fee". It would add an ad SDK, a privacy policy, and a consent screen. |

What the sources agree on: avoid pay-to-win. Cosmetic and convenience purchases convert
best and players like them most.

## Recommendation

1. **Launch free on Google Play with a "Supporter Pack" in-app purchase** (one-time,
   about $3–5): alternative player sprites, gem palettes, and a name on a supporters
   screen. It changes nothing in gameplay, and the daily run stays fair.
2. **Also sell the APK** as pay-what-you-want on itch.io (Shattered PD does this).
3. **Consider rewarded ads only after measuring retention.** Hardcore and daily runs
   would never show ads.

## Technical feasibility (Kivy / python-for-android)

- **In-app purchases:** there is no maintained Kivy wrapper for the current Play Billing
  Library. *IABwrapper* targets the old v3 API ([PyPI](https://pypi.org/project/IABwrapper)).
  The route that works is a small Java helper around Play Billing, built in through
  python-for-android and called from Python with pyjnius
  ([Kivy Android guide](https://kivy.org/docs/guide/android.html)).
  It needs a test on a device. **Effort: medium.**
- **Rewarded ads:** *KivMob* supports AdMob rewarded video. Its quickstart pins
  `android.api = 33`, but Play requires 36, so check that it still works first
  ([PyPI](https://pypi.org/project/kivmob)).
  *KivAds* is an alternative ([docs](https://kivads.readthedocs.io/en/latest/Rewarded.html)).
- Gameplay code stays in `game/`. Purchases only unlock cosmetics, and the Kivy frontend
  applies them through `mobile/sprites.py`.

## What it needs from you

- Google Play Console account (one-time fee), payments profile, app id (`package.domain`
  in `mobile/buildozer.spec`), and a signed AAB (see `docs/ANDROID.md`).
- A privacy policy URL. Play requires one for any app, and ads make it essential.
- A decision on licensing. The repo is MIT, so anyone may rebuild the game. That is the
  same trade-off Shattered PD accepts with GPLv3: players pay for convenience and to
  support the developer, not for access. If you would rather keep the art or sounds
  proprietary, they would have to leave the public repo.
