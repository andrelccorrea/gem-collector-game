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
