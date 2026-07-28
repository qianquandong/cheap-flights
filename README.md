# cheap-flights

A [Claude Code](https://claude.com/claude-code) skill that answers two questions together:

1. **When should I take this trip?** — ranks date windows by how many days off you get per vacation day burned, against your own company holiday calendar.
2. **What's the cheapest way to fly it?** — prices those windows through Google Flights, with the flexibility levers a careful person would actually run.

Most flight tools answer only the second question. The first one is usually worth more: bridging a company holiday can buy you three extra days off for free, which beats any fare trick below.

## Install

```bash
git clone https://github.com/qianquandong/cheap-flights ~/.claude/skills/cheap-flights
```

Then install [`fli`](https://github.com/punitarani/fli), which reads Google Flights with no API key:

```bash
pipx install flights && pipx inject flights click
```

The `inject` is not optional — `flights` 0.9.0 declares `typer` but not `click`, so a plain install gives you `ModuleNotFoundError: No module named 'click'` on the first run.

Set up your calendar:

```bash
cp holidays.example.txt holidays.txt   # then edit it
python3 pto.py --demo                  # self-check, prints "ok"
```

`holidays.txt` is gitignored. It holds your employer's holiday dates and your PTO balance — keep it local.

## Use

In Claude Code, just ask. The skill triggers on flight and vacation-planning questions in English or Chinese:

> find me a cheap flight to Shanghai sometime in the next year

Or drive the pieces directly:

```bash
python3 pto.py --from 2026-08-01 --to 2027-06-23 --min-days 10 --max-days 18
```

```
depart       return       days off  PTO used  days/PTO  holidays used
2026-12-24   2027-01-03         11         4       2.8  Christmas Eve, Christmas Day, New Year's Day
2026-11-20   2026-11-29         10         4       2.5  Thanksgiving, day after Thanksgiving
```

Then price a window:

```bash
fli dates DFW PVG --from 2026-11-20 --to 2026-11-29 --round --duration 10 --format json
```

## What it actually checks

- **Date flexibility** — usually the single biggest lever, and one command.
- **Nearby airports** — origin and destination metro alternates.
- **Southwest**, separately. Southwest doesn't list on Google Flights, so `fli` cannot see it. On US domestic routes this is the most common way to quote a wrong "cheapest".
- **Split one-ways** vs. round-trip — sometimes a 15–30% win domestically, sometimes worse than the round-trip; it gets checked rather than assumed.
- **Real cost** — re-prices finalists with bags and without basic economy, because a $123 fare with a $60 carry-on isn't cheaper than a $150 fare with two free bags.

## Configure

- **Home airports** — edit the Defaults section of `SKILL.md`. It ships with `DFW`/`DAL`.
- **Holidays and PTO** — `holidays.txt`. One `YYYY-MM-DD  Name` per line, plus `BALANCE n`.

## Limits

- Google Flights publishes roughly 11 months of inventory. Ask for dates beyond that and you get nothing — not an error, just no data.
- `fli` is a scraper. It breaks when Google changes things; the skill falls back to reading the page in a browser and is instructed never to substitute a remembered price for a failed lookup.
- Fares 8+ months out are thin and move a lot. Treat them as shape, not as quotes.
- No points or award travel. For that, see [borski/travel-hacking-toolkit](https://github.com/borski/travel-hacking-toolkit).
- The skill never books anything and never enters payment or passport details. It hands you links.

## License

MIT. Flight data comes from [`fli`](https://github.com/punitarani/fli) (MIT), which is not affiliated with Google.
