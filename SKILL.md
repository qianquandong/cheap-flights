---
name: cheap-flights
description: Find the cheapest realistic way to fly a given route, and pick trip dates that burn the fewest vacation days. Use when the user asks to find flights, check airfare, "机票", "便宜机票", "查一下飞X的机票", asks whether to book now or wait, asks when to take a trip, how to use their PTO, annual leave, or school break, "寒假", "暑假", "年假", or gives an origin/destination and dates. Uses the `fli` CLI for Google Flights data plus a separate Southwest check, ranks trip windows against the user's own calendar of company holidays or academic breaks (looking up a school's academic calendar if given the school name), applies flexibility levers (flexible dates, nearby airports, split one-ways, bag-inclusive pricing), and returns 3 priced options.
---

# Cheap Flights

Find the cheapest *bookable* fare for a route, then hand the user links. Never book, never enter payment or passport details — that is the user's action.

## Defaults (skip asking unless it matters)

- Origin: **edit this line to your own home airports.** Currently `DFW`, and always also check `DAL` (Love Field) — Southwest hub, so Google Flights can't see it.
- Round-trip, 1 adult, economy, no checked bag.
- Ask only for what you can't default: destination and rough dates. If dates are vague ("sometime in October"), that's *good* — use the price graph.

## Tooling

`fli` ([punitarani/fli](https://github.com/punitarani/fli), MIT) is installed via pipx and reads Google Flights directly. No API key. Always pass `--format json` — the default output is Rich boxes that truncate columns.

```bash
fli flights DFW NRT 2026-10-12 --return 2026-10-22 --format json --sort CHEAPEST
fli dates DFW NRT --from 2026-10-01 --to 2026-11-01
```

Useful flags: `--stops 0` · `--bags N` · `--carry-on` · `--exclude-basic` (prices real cost, see step 3) · `--class` · `--time` · `--airlines`/`-A` · `--max-layover`.

**Everything priced here comes from Google.** `fli` is a Google Flights scraper and the browser fallback is the same site, so the two failure modes need different responses — do not treat them alike.

**A. `fli` broke but Google is reachable** (parse errors, empty results on a route that obviously has flights). The scraper rotted. Retry once, then read the page directly in the browser pane:
`https://www.google.com/travel/flights?q=Flights%20from%20DFW%20to%20NRT%20on%202026-10-12%20through%202026-10-22`
(`preview_start` → `get_page_text`; WebFetch returns nothing, the page is JS-rendered).

**B. Google itself is unreachable** — `Could not reach Google Flights`, timeouts, or the browser pane failing to load google.com at all. **The most likely cause is that the user is in mainland China**, where Google is blocked; the browser fallback is on the same domain and will fail identically, so do not walk them through it. Say plainly which it is and offer:

- Turn on a VPN, then re-run — everything below works unchanged.
- Or price it on a site reachable from China. `trip.com` / 携程 is the obvious one, driven through the browser pane (`preview_start` → `read_page`). **This path is untested** — treat the first run as an experiment and tell the user so.
- For flights *departing* China, the domestic sites are often cheaper than Google anyway, so this is not purely a downgrade.

Note that `pto.py` needs no network at all. When Google is unreachable you can still deliver the whole calendar half — the ranked windows — and only the pricing is blocked. Lead with what you *can* answer.

Never substitute remembered prices for a failed lookup, under either failure mode.

Install note if it ever breaks: `flights` 0.9.0 ships without `click` even though `typer` needs it — `pipx inject flights click`. The `fli-mcp` binary is unusable without the `mcp` extra; we drive the CLI from Bash instead, deliberately.

## Holidays, school breaks, and leave

When the user's dates are open ("sometime this fall", "从现在到明年"), pick the *window* before pricing it. `pto.py` ranks windows by days off gained per day of leave burned — bridging a holiday, or landing inside a school break, is usually worth more than any fare lever below.

```bash
python3 pto.py --from 2026-08-01 --to 2027-06-23 --min-days 10 --max-days 18
```

It reads `holidays.txt` (gitignored, user-maintained; `holidays.example.txt` is the template). Single days and ranges both work — `2026-12-19..2027-01-11  Winter break`. `BALANCE n` caps suggestions at the leave the user actually has; a student with no leave to spend sets `BALANCE 0` and gets only windows that cost nothing.

### Bootstrapping the calendar

If `holidays.txt` doesn't exist, don't just refuse — offer to build it. Ask which they are:

- **Working** — ask for the employer's holiday list. Company holiday calendars are usually internal, so this generally means the user pastes it from HR. Do not guess it from the company name.
- **Student** — ask for the school name. Academic calendars are public: search for `<school> academic calendar <year>`, read the registrar's page, and draft the ranges.

Then, whichever path:

1. **Show the drafted lines to the user before writing them**, with the source URL and the academic year or calendar year they came from.
2. Write `holidays.txt` only after the user confirms. Keep the source URL in a `#` comment so the next session can tell where the dates came from and how stale they are.
3. If the search turns up the wrong year, an unofficial aggregator, or nothing authoritative, say so and ask the user to paste the dates instead.

**Never write a date into `holidays.txt` that you did not read from a source or receive from the user.** A plausible-looking wrong break date produces a confidently wrong trip window and the user has no way to notice — this is the one place in this skill where a quiet guess does real damage. US federal holidays are the only safe exception, and they are not the same as either an employer's or a school's calendar.

### Using the windows

- Take the top 2–3 windows, then price each with `fli dates`. The cheapest fare inside a bad window loses to a decent fare that costs three fewer days of leave.
- Break windows are also peak-fare windows — spring break and winter break are the two most expensive weeks of the year on many routes. Expect the bridge to cost more per ticket and say so explicitly. The tradeoff is days against dollars, and only the user can weigh those.
- For students, also price the shoulder: leaving two days into the break or coming back two days early is often a few hundred dollars cheaper and costs no class time.

## Procedure

0. **If dates are open, run `pto.py` first** and price its top windows rather than the whole range.

1. **Get a baseline** — `fli flights <ORIG> <DEST> <DATE> --format json`, then the same for `DAL` if US domestic.

2. **Run the flexibility levers.** Each one is a separate check; report which ones moved the price:

   - **Date flexibility** — `fli dates` over ±3 days, or the whole month if dates are soft. Usually the single biggest lever, and it's one command.
   - **Nearby airports** — DFW ↔ DAL on the origin side; destination metro alternates (NRT/HND, LGW/LHR/STN, EWR/JFK/LGA, ONT/BUR/LAX).
   - **Southwest is invisible to Google Flights — and therefore to `fli`.** For any US domestic route out of Dallas, check `southwest.com` in the browser pane separately or you will quote a wrong "cheapest". Bags fly free there, which often flips the ranking. This is the single most common way to be wrong on a DFW/DAL route.
   - **Split one-ways** — two `fli flights` one-way calls instead of one `--return`. Common 15–30% win on domestic; adds a missed-connection risk worth one sentence of warning.
   - **Tue/Wed departures, red-eyes, early-morning banks.**
   - **Booking window** — domestic sweet spot ~1–3 months out, international ~2–8 months. If the user is inside 2 weeks, say so plainly: prices only go up from here, book now.

3. **Normalize to real cost before comparing.** Re-run the finalists with `--bags N --carry-on --exclude-basic` so the fares are comparable. A $123 Frontier fare with a $60 carry-on is not cheaper than a $150 Southwest fare with two free checked bags — this reordering happens constantly on Dallas routes.

4. **Output — exactly three options:**

   | | Route | Price (all-in) | Time | Book |
   |---|---|---|---|---|
   | Cheapest | ... | $X | Xh, N stops | link |
   | Best value | ... | $X | ... | link |
   | Most convenient | ... | $X | ... | link |

   Then two lines: which lever produced the saving, and the volatility caveat ("quoted as of <date>; fares move daily").

## Rules

- Prices are only real if `fli` or the browser returned them this session. Never quote an airfare from memory or from a training-data recollection of "typical" prices.
- Sanity-check the cheapest result before presenting it. `fli` sorts on price alone and will happily return DFW→MCO→LAX at eleven hours. If the cheapest option is absurd, show it *and* the sane one.
- Mention Skiplagged / hidden-city only if the user asks. One line: it can void the return leg and get you banned from the loyalty program. Never make it the recommendation.
- Points/miles redemptions: out of scope unless asked.
- Error-fare monitoring (Going.com, Secret Flying) is a *subscribe and wait* play, not an answer to "find me a flight next Tuesday". Only surface it when the user's dates are open-ended.
