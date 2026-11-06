import numpy as np

def date_to_doy(year, month, day):
    """Fixed mapping by month and day. Uses leap-year cumulative days.
    Non-leap years have no day 60 (Feb 29 doesn't exist)."""
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Test
test_cases = [
    (1992, 1, 1, 1),
    (1992, 2, 28, 59),
    (1992, 2, 29, 60),
    (1992, 3, 1, 61),
    (1992, 12, 31, 366),
    (1993, 1, 1, 1),
    (1993, 2, 28, 59),
    (1993, 3, 1, 61),
    (1993, 12, 31, 366),  # Fixed mapping, so Dec 31 = 366 even in non-leap
    (1996, 2, 29, 60),
    (2000, 2, 29, 60),
    (2001, 3, 1, 61),
    (2001, 12, 31, 366),
]

for y, m, d, expected in test_cases:
    result = date_to_doy(y, m, d)
    ok = "OK" if result == expected else "FAIL"
    print(f"{y}-{m:02d}-{d:02d} -> doy {result} (expected {expected}) {ok}")
