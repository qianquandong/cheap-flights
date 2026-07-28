---
name: cheap-flights
description: Find the cheapest realistic way to fly a route. Use when the user asks to find flights, check airfare, compare fares, "机票", "便宜机票", "查一下飞X的机票", asks whether to book now or wait, or gives an origin and destination. Collects route, dates, cabin, passengers and airline preference, prices them through the `fli` CLI plus a separate Southwest check, applies flexibility levers (nearby airports, split one-ways, bag-inclusive pricing), and returns three priced options.
---

# Cheap Flights

Find the cheapest *bookable* fare for a route and hand the user links. Never book, never enter payment or passport details — that is the user's action.

## Inputs

Ask for whatever the user hasn't already given, in one message, not one at a time:

| | | passed as |
|---|---|---|
| **出发地** origin | IATA code or city | positional |
| **目的地** destination | IATA code or city; `fli airports <city>` resolves names | positional |

| **日期** dates | depart, and return if round-trip | positional + `--return` |
| **舱位** cabin | ECONOMY / PREMIUM_ECONOMY / BUSINESS / FIRST | `--class` |
| **人数** passengers | see the caveat below | — |
| **航司** airline | preferred or excluded, or none | `--airlines` / `--exclude-airlines` |

Defaults when the user doesn't care: round-trip, economy, 1 adult, no airline preference. If dates are flexible, say so — that is the biggest lever available and `fli dates` costs one command.

**`fli airports` only understands English.** `fli airports 上海` and `fli airports 达拉斯` both return "No airports found" — the lookup is English-only even though this skill is triggered by Chinese phrasing. Translate the city to English yourself before calling it, or go straight to the IATA code when you know it. Never report "no such airport" to the user off a Chinese query; that's the tool's limit, not a fact about the world.

**Passengers is a question the tool can't fully answer.** The CLI always prices one adult; `PassengerInfo` exists in the library but is not exposed. For more than one passenger, quote the per-person fare, say explicitly that it is per person for one adult, and put the passenger count in the search URL so the user confirms the real total on the page. Never multiply the fare by the headcount — when only a few seats remain in a fare bucket, a larger party reprices to the next bucket.

## Tooling

`fli` ([punitarani/fli](https://github.com/punitarani/fli), MIT), installed via pipx. No API key. Always pass `--format json` — the default output is Rich boxes that truncate columns.

```bash
fli flights DFW PVG 2026-10-01 --return 2026-10-15 --class ECONOMY --format json --sort CHEAPEST
fli dates DFW PVG --from 2026-10-01 --to 2026-11-01 --round --duration 14
fli airports shanghai
```

Useful flags: `--stops 0` · `--bags N` · `--carry-on` · `--exclude-basic` · `--time` · `--max-layover` · `--alliance`.

**Google is the only data source.** `fli` is a Google Flights scraper, so it rots. On parse errors or empty results for a route that obviously has flights, retry once, then read the page in the browser pane:
`https://www.google.com/travel/flights?q=Flights%20from%20DFW%20to%20PVG%20on%202026-10-01%20through%202026-10-15`
(`preview_start` → `get_page_text`; WebFetch returns nothing, the page is JS-rendered).

If google.com won't load at all, the fallback is on the same domain and will fail the same way — say Google is unreachable and stop, rather than walking the user through a second dead end. There is no non-Google backend and adding one is out of scope.

Install note if it ever breaks: `flights` 0.9.0 ships without `click` even though `typer` needs it — `pipx inject flights click`.

## Procedure

1. **Baseline** — `fli flights <ORIG> <DEST> <DATE> [--return <DATE>] --class <CABIN> --format json`. Add `--airlines`/`--exclude-airlines` only if the user expressed a preference; constraining early hides cheaper options.

2. **Run the flexibility levers.** Each is a separate check; report which ones actually moved the price and which didn't.

   - **Date flexibility** — `fli dates` across the range, or ±3 days. Usually the single biggest lever, and it's one command.
   - **Nearby airports** — origin and destination metro alternates (DFW/DAL, NRT/HND, LGW/LHR/STN, EWR/JFK/LGA, ONT/BUR/LAX, PVG/SHA). Read the arrival airport off the returned legs, not off the `query` echo in the JSON — the echo just repeats what you asked for, so it cannot tell you whether the alternate produced different flights or Google quietly served the same metro.
   - **Southwest is invisible to Google Flights — and therefore to `fli`.** For any US domestic route, check `southwest.com` in the browser pane separately or you will quote a wrong "cheapest". Bags fly free there, which often flips the ranking. What's confirmed about this check:
     - The site renders in the browser pane and `get_page_text` reads it fine, so the check is executable.
     - **Deep links mostly don't work.** `select.html?originationAirportCode=DAL&destinationAirportCode=LAX&departureDate=…` redirects to the homepage and carries only the origin — destination, dates and trip type are all dropped. Fill the form fields and submit; there is no URL shortcut.
     - **Southwest books a much shorter horizon than Google.** The homepage states it outright ("Now accepting reservations through April 05, 2027" as of 2026-07-28 — roughly eight months). Read that line before searching: past it Southwest has nothing, and the check is a waste of the user's time rather than a gap in your answer. Say you skipped it and why.
     - Submitting the search form is a user-visible action on an external site — get the user's OK before doing it rather than assuming.
   - **Split one-ways** — two one-way `fli flights` calls instead of one `--return`. Sometimes 15–30% cheaper domestically, sometimes much worse; check rather than assume. Measured once on DFW–PVG: $667 + $618 against an $888 round-trip, so the round-trip won by $397.
   - **Booking window** — domestic sweet spot ~1–3 months out, international ~2–8 months. Inside two weeks, say plainly that prices only go up from here.

3. **Normalize to real cost.** Re-run the finalists with `--bags N --carry-on --exclude-basic` so the fares are comparable. A $123 fare with a $60 carry-on is not cheaper than a $150 fare with two free checked bags.

4. **Output — exactly three options:**

   | | Route | Price (all-in) | Time | Search |
   |---|---|---|---|---|
   | Cheapest | ... | $X | Xh, N stops | link |
   | Best value | ... | $X | ... | link |
   | Most convenient | ... | $X | ... | link |

   The column is **Search, not Book** — `fli` has no `booking` subcommand and its JSON carries only a `booking_token`, never a URL, so no specific itinerary can be deep-linked. Build a Google Flights search URL naming the airline so the result lands near the top:
   `https://www.google.com/travel/flights?q=Flights%20from%20DFW%20to%20PVG%20on%202026-10-01%20through%202026-10-15%20on%20Cathay%20Pacific`
   Don't label it "Book" and don't imply one click finishes the job.

   Then two lines: which lever produced the saving, and the volatility caveat ("quoted as of <date>; fares move daily").

   If the three rows collapse — same carrier, same price, only the times differ — say that instead of padding the table. On many long-haul routes the honest answer is two options, not three: the cheap connection and the expensive nonstop, with nothing meaningful between them.

## Rules

- Prices are only real if `fli` or the browser returned them this session. Never quote an airfare from memory or from a training-data recollection of "typical" prices.
- Sanity-check the cheapest result before presenting it. `fli` sorts on price alone and will happily return DFW→MCO→LAX at eleven hours. If the cheapest option is absurd, show it *and* the sane one.
- Mention Skiplagged / hidden-city only if the user asks. One line: it can void the return leg and get you banned from the loyalty program. Never make it the recommendation.
- Points/miles redemptions: out of scope. Point at [borski/travel-hacking-toolkit](https://github.com/borski/travel-hacking-toolkit).
- Visas, transit rules and entry requirements are out of scope — a routing through a third country can be unbookable for reasons this skill cannot see. Don't advise on them; don't pretend the cheapest routing is necessarily usable.
