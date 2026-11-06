
import numpy as np

# Verify day-of-year mapping
def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

from datetime import datetime
test_cases = [
    (datetime(1992, 1, 1), 1),
    (datetime(1992, 2, 28), 59),
    (datetime(1992, 2, 29), 60),
    (datetime(1992, 3, 1), 61),
    (datetime(1992, 12, 31), 366),
    (datetime(1993, 2, 28), 59),  # non-leap
    (datetime(1993, 3, 1), 61),   # non-leap, but still 61
    (datetime(1993, 12, 31), 366),
    (datetime(1991, 12, 31), 366),  # extension
    (datetime(2003, 1, 1), 1),      # extension
]

for dt, expected in test_cases:
    got = doy_from_date(dt)
    status = "OK" if got == expected else f"FAIL (expected {expected})"
    print(f"{dt.date()}: got {got}, expected {expected} -> {status}")
