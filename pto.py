#!/usr/bin/env python3
"""Rank trip windows by days off gained per day of leave burned.

    ./pto.py --from 2026-08-01 --to 2027-06-23 --min-days 10 --max-days 21

Works off any calendar of free days — company holidays, or a school's academic
breaks. Reads holidays.txt (see holidays.example.txt). Stdlib only.
"""

import argparse
import datetime as dt
from pathlib import Path

DEFAULT_FILE = Path(__file__).with_name("holidays.txt")


MAX_SPAN = 366  # a single break longer than a year is a typo, not a vacation


def load(path):
    """-> ({date: name}, balance or None).

    Lines: 'YYYY-MM-DD  Name' | 'YYYY-MM-DD..YYYY-MM-DD  Name' (school breaks) |
    'BALANCE n' | '# comment'.
    """
    holidays, balance = {}, None
    for lineno, raw in enumerate(Path(path).read_text().splitlines(), 1):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        head, _, rest = line.partition(" ")
        name = rest.strip() or "holiday"

        if head.upper() == "BALANCE":
            try:
                balance = int(rest.strip())
            except ValueError:
                raise SystemExit(f"{path}:{lineno}: BALANCE needs a whole number of days, got {rest.strip()!r}")
            continue

        try:
            lo, sep, hi = head.partition("..")
            start = dt.date.fromisoformat(lo)
            end = dt.date.fromisoformat(hi) if sep else start
        except ValueError:
            raise SystemExit(
                f"{path}:{lineno}: expected 'YYYY-MM-DD  Name', 'YYYY-MM-DD..YYYY-MM-DD  Name', "
                f"or 'BALANCE n', got {raw!r}")
        if end < start:
            raise SystemExit(f"{path}:{lineno}: range ends before it starts: {raw!r}")
        if (end - start).days + 1 > MAX_SPAN:
            raise SystemExit(f"{path}:{lineno}: range spans {(end - start).days + 1} days — typo? {raw!r}")

        while start <= end:
            holidays[start] = name
            start += dt.timedelta(days=1)
    return holidays, balance


def pto_cost(start, end, holidays):
    """Weekdays in [start, end] that aren't already free — i.e. PTO days, or classes missed."""
    day, n = start, 0
    while day <= end:
        if day.weekday() < 5 and day not in holidays:
            n += 1
        day += dt.timedelta(days=1)
    return n


def rank(lo, hi, holidays, min_days, max_days, balance=None):
    out = []
    day = lo
    while day <= hi:
        for length in range(min_days, max_days + 1):
            end = day + dt.timedelta(days=length - 1)
            if end > hi:
                break
            cost = pto_cost(day, end, holidays)
            if balance is not None and cost > balance:
                continue
            # cost 0 (window is entirely weekends/holidays) sorts top, no division by zero
            out.append({"start": day, "end": end, "days": length, "pto": cost,
                        "ratio": length / max(cost, 0.5)})
        day += dt.timedelta(days=1)
    out.sort(key=lambda w: (-w["ratio"], w["pto"], w["start"]))
    return out


def dedupe(windows, top):
    """Drop windows overlapping a better one already picked — otherwise the top 10 is one trip 10 times."""
    picked = []
    for w in windows:
        if any(w["start"] <= p["end"] and p["start"] <= w["end"] for p in picked):
            continue
        picked.append(w)
        if len(picked) == top:
            break
    return picked


def demo():
    # Thanksgiving 2026 falls Thu 11-26 / Fri 11-27. Sat 11-21 → Sun 11-29 is 9 days off
    # for 3 PTO days (Mon-Wed 11-23..25); the weekends and the two holidays are free.
    hol = {dt.date(2026, 11, 26): "Thanksgiving", dt.date(2026, 11, 27): "Day after"}
    assert pto_cost(dt.date(2026, 11, 21), dt.date(2026, 11, 29), hol) == 3
    assert pto_cost(dt.date(2026, 11, 21), dt.date(2026, 11, 22), hol) == 0  # a bare weekend costs nothing
    assert pto_cost(dt.date(2026, 11, 23), dt.date(2026, 11, 25), {}) == 3  # no holidays -> every workday counts

    best = rank(dt.date(2026, 11, 1), dt.date(2026, 12, 15), hol, 9, 9)[0]
    assert best["pto"] == 3 and best["days"] == 9, best
    assert best["start"] == dt.date(2026, 11, 21), best  # the Thanksgiving bridge wins on its own

    over = rank(dt.date(2026, 11, 1), dt.date(2026, 12, 15), hol, 9, 9, balance=2)
    assert all(w["pto"] <= 2 for w in over)  # balance is a hard filter

    assert len(dedupe(rank(dt.date(2026, 11, 1), dt.date(2026, 12, 15), hol, 9, 9), 3)) <= 3

    # Student case: a break written as a range costs zero leave, so it outranks everything.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("# school\nBALANCE 0\n2026-12-19..2027-01-03  Winter break\n")
        tmp = f.name
    days, bal = load(tmp)
    assert bal == 0 and len(days) == 16, (bal, len(days))
    assert days[dt.date(2026, 12, 25)] == "Winter break"
    assert pto_cost(dt.date(2026, 12, 19), dt.date(2027, 1, 3), days) == 0
    top = rank(dt.date(2026, 12, 1), dt.date(2027, 1, 31), days, 10, 16, balance=0)[0]
    assert top["pto"] == 0, top

    for bad in ("2026-13-01  nope\n", "2026-12-05..2026-12-01  backwards\n", "BALANCE lots\n",
                "2020-01-01..2026-01-01  typo\n"):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(bad)
        try:
            load(f.name)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"bad input accepted: {bad!r}")
    print("ok")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="lo", type=dt.date.fromisoformat)
    p.add_argument("--to", dest="hi", type=dt.date.fromisoformat)
    p.add_argument("--min-days", type=int, default=7)
    p.add_argument("--max-days", type=int, default=21)
    p.add_argument("--holidays", default=DEFAULT_FILE)
    p.add_argument("--balance", type=int, help="override BALANCE from the holidays file")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--demo", action="store_true", help="run self-check and exit")
    a = p.parse_args()

    if a.demo:
        return demo()
    if not a.lo or not a.hi:
        p.error("--from and --to are required")

    if not Path(a.holidays).exists():
        raise SystemExit(f"{a.holidays} not found — copy holidays.example.txt and fill in your calendar")

    holidays, file_balance = load(a.holidays)
    balance = a.balance if a.balance is not None else file_balance
    windows = dedupe(rank(a.lo, a.hi, holidays, a.min_days, a.max_days, balance), a.top)
    if not windows:
        raise SystemExit("no window fits — raise --balance or widen the date range")

    print(f"{'depart':<12} {'return':<12} {'days off':>8} {'leave used':>11} {'ratio':>6}  free days used")
    for w in windows:
        used = dict.fromkeys(n for d, n in sorted(holidays.items()) if w["start"] <= d <= w["end"])
        print(f"{w['start']!s:<12} {w['end']!s:<12} {w['days']:>8} {w['pto']:>11} "
              f"{w['ratio']:>6.1f}  {', '.join(used) or '—'}")
    if balance is not None:
        print(f"\nfiltered to windows costing <= {balance} days of leave")


if __name__ == "__main__":
    main()
