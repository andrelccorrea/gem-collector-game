# Balance log

Measured with the headless bot (`game/bot.py`) through the real game rules:

```bash
uv run python scripts/balance_sim.py --seeds 10 --minutes 60
```

The bot is greedy and efficient (always digs the nearest workable spot, sells when its
bag holds 12 items, buys the cheapest affordable tool or upgrade). Human players are
slower, so treat its times as a lower bound. "Gems by biome" is the raw value of the gems
found there.

## Baseline (before Phase 2 gameplay changes)

```
 seed  win (min)  died  gold/min  gems by biome ($ raw)
    1       12.2 False       830  cave 2762, hillside 3135, river 3915
    2       14.8 False       678  cave 2930, hillside 3530, meadow 60, river 2938
    3       15.9 False       655  cave 2192, hillside 2289, meadow 141, river 5451
    4       15.2 False       666  cave 2063, hillside 2863, meadow 39, river 4754
    5       13.4 False       753  cave 2946, hillside 3107, meadow 8, river 3620
    6       16.1 False       621  cave 1650, hillside 3039, meadow 52, river 4709
    7       16.0 False       631  cave 2330, hillside 3256, meadow 314, river 3725
    8       16.0 False       645  cave 1733, hillside 3019, meadow 565, river 4647
    9       14.3 False       710  cave 2292, hillside 3577, meadow 65, river 3716
   10       13.2 False       773  cave 1390, hillside 3655, meadow 44, river 4769

won 10/10, died 0
median minutes to win: 15.0
median gold/min: 672
```

Observations:

- **Short:** an efficient run reaches $10,000 in ~15 minutes of game time.
- **No risk:** 0 deaths in 10 runs. Enemies do not threaten a player who fights back.
- **Biomes unbalanced:** the River Delta pays the most; the Meadow is nearly worthless
  (its gems are cheap), so there is no reason to go there after the first minutes.
- **No reason to go home:** inventory is unlimited; only HP sends the player back.

## After tool tiers, bag capacity, loot-only kills and staged stock

```

won 10/10, died 0
median minutes to win: 15.3
median gold/min: 663
```

Barely changed (median 15.0 -> 15.3 min). Most income comes from gems lying visible on
the map and from panning river water, which tool tiers do not gate, and the bot already
sold every 12 items (below the new 15-item bag). Pacing has to come from prices that
react to flooding the market, the lantern and enemy pressure.

## After market saturation (prices drop 6% per recent sale, recover 1 sale per 20 s)

```
won 10/10, died 0
median minutes to win: 21.8
median gold/min: 477
```

The biggest single pacing lever so far (15.3 -> 21.8 min): dumping a bag of one gem kind
now pays noticeably less, rewarding variety and spreading sales out.

## After the lantern

Unchanged for the bot (median 21.8 min): it heads home to sell often enough that its
lantern rarely runs low. The lantern mainly limits how far into the caves a human can
push before the view shrinks (2.5 fuel/s there vs 0.5 in the meadow).

## Bot uses its whole bag; market retuned

Until now the bot sold at 12 items. Once it filled the real bag (15, upgradable to 60),
it made fewer trips and got *faster* (median 13.3 min): with 6%/sale saturation, big
batches were barely penalized, so bigger bags simply meant more digging time.

Sweep over the market parameters (8 seeds, bot sells everything at once — a worst case):

| price drop per sale | recovery per sale | won | median min | gold/min |
|---|---|---|---|---|
| 6%  | 20 s | 8/8 | 13.3 | 804 |
| 10% | 30 s | 8/8 | 16.3 | 674 |
| 15% | 30 s | 6/8 | 16.5 | 608 |
| 15% | 45 s | 3/8 | 18.3 | 156 |
| 25% | 45 s | 0/8 | -    | 144 |

Chosen: **10% per sale, one sale recovered every 30 s** — every run still wins, and
selective selling (which the bot does not do) is clearly rewarded. 10 seeds:

```
won 10/10, died 0
median minutes to win: 16.1
median gold/min: 685
```

## New gear, regrowth and a soft-lock (2026-10-09)

The bot buys the cheapest affordable tool or upgrade, so it now also buys armor, boots,
the dowsing rod and the drill (it ignores supplies, the dog, outfits and contracts).

**Soft-lock found:** with the drill, 2 of 10 seeds dug out every spot the bot could reach
in ~16 min and stalled at $9,417 earned (157 gold/min over the hour): nothing left to
dig, and a bag not full enough to send it home. A slow human could hit the same wall.
Fixes: worked-out ground regrows one game day (6 min) after it was dug or panned
(`game/regrow.py`), the bot sells when it finds nothing to work, and saves now keep the
game clock (so days, deals, contracts, weather and regrowth carry over a load).

Pacing levers measured (10 seeds, median minutes to win; previous baseline 16.1):

| change | median min | gold/min |
|---|---|---|
| all new gear, boots x0.85/x0.7 | 14.0 | 733 |
| drill at 1000 / 1500 gold (instead of 600) | 13.9 / 13.8 | 742 / 765 |
| boots disabled | 15.7 | 646 |
| boots x0.9/x0.8 | 14.7 | 708 |
| **chosen: boots x0.9/x0.8 at 200/500 gold** | 13.8 | 738 |

The boots, not the drill, explain most of the speed-up; differences under about a minute
are within seed noise. The bot remains a lower bound for humans, and still never dies:
enemies stay a light threat for a player who fights back.

```
won 10/10, died 0
median minutes to win: 13.8
median gold/min: 738
```
