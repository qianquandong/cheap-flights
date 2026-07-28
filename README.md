# cheap-flights

A [Claude Code](https://claude.com/claude-code) skill that finds the cheapest realistic way to fly a route — and tells you which of its tricks actually worked.

You give it origin, destination, dates, cabin, passengers and any airline preference. It prices them through Google Flights, then runs the flexibility levers a careful person would run by hand: nearby airports, flexible dates, split one-ways, and a separate Southwest check that Google Flights can't see. It reports which levers moved the price and which didn't.

It does not book anything.

## Install

```bash
git clone https://github.com/qianquandong/cheap-flights ~/.claude/skills/cheap-flights
pipx install flights && pipx inject flights click
```

The `inject` is not optional — [`flights`](https://github.com/punitarani/fli) 0.9.0 declares `typer` but not `click`, so a plain install gives you `ModuleNotFoundError: No module named 'click'` on the first run. No API key is needed.

## Use

Ask in English or Chinese:

> find me a cheap flight from Dallas to Shanghai, October, economy

Or drive `fli` directly:

```bash
fli dates DFW PVG --from 2026-10-01 --to 2026-11-01 --round --duration 14
fli flights DFW PVG 2026-10-01 --return 2026-10-15 --bags 1 --exclude-basic --format json
```

## What it checks

- **Date flexibility** — usually the biggest lever, and one command.
- **Nearby airports** — origin and destination metro alternates, verified against the arrival airport in the results rather than the query echo.
- **Southwest**, separately. Southwest doesn't list on Google Flights, so `fli` cannot see it. On US domestic routes this is the most common way to quote a wrong "cheapest".
- **Split one-ways vs round-trip** — sometimes a 15–30% domestic win, sometimes far worse. Checked, not assumed.
- **Real cost** — re-prices finalists with bags and without basic economy, because a $123 fare with a $60 carry-on isn't cheaper than a $150 fare with two free bags.

## Limits

These are the known holes, stated plainly rather than discovered later.

- **Google is the only data source**, so it has to be reachable. Where it isn't — mainland China, most notably — this skill doesn't work and doesn't try to; there's no alternate backend.
- **No booking links.** `fli` has no `booking` subcommand and its JSON carries only a `booking_token`, never a URL, so the skill hands you a Google Flights *search* URL, not a deep link to the itinerary.
- **One passenger.** The CLI always prices a single adult. `PassengerInfo` exists in the library but isn't exposed, so multi-passenger totals have to be confirmed on the search page — the skill won't multiply a fare by headcount, because a larger party can reprice into the next fare bucket.
- **The Southwest check is untested.** It's the loudest claim in the skill and nobody has yet driven southwest.com through the browser pane to confirm it works.
- Google Flights publishes roughly 11 months of inventory. Ask for dates beyond that and you get nothing — not an error, just no data.
- `fli` is a scraper and breaks when Google changes things. The skill falls back to reading the page in a browser and is instructed never to substitute a remembered price for a failed lookup.
- Fares 8+ months out are thin and move a lot. Treat them as shape, not quotes.
- No points or award travel — see [borski/travel-hacking-toolkit](https://github.com/borski/travel-hacking-toolkit). No visa or transit-rule advice: the cheapest routing isn't always one you can legally use.

## License

MIT. Flight data comes from [`fli`](https://github.com/punitarani/fli) (MIT), which is not affiliated with Google.
