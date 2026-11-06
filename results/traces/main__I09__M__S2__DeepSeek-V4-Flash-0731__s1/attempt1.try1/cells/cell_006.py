
import numpy as np
import pandas as pd

# Define DOY mapping: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366
# This is the leap-year day numbering used for all years.

def date_to_doy(date):
    """Convert a date (datetime64 or Python date) to DOY in 1-366 leap-year numbering."""
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Test
test_dates = [
    ('1992-01-01', 1),
    ('1992-02-28', 59),
    ('1992-02-29', 60),
    ('1992-03-01', 61),
    ('1992-12-31', 366),
    ('2022-01-01', 1),
    ('2022-02-28', 59),
    ('2022-03-01', 61),
    ('2022-06-01', 153),
    ('2022-06-30', 182),
    ('2022-07-01', 183),
    ('2022-07-31', 213),
    ('2022-08-01', 214),
    ('2022-08-31', 244),
    ('1991-12-27', 361),  # Dec 27 in leap numbering
    ('2003-01-05', 5),
]
for d, expected in test_dates:
    got = date_to_doy(d)
    status = "OK" if got == expected else f"FAIL (expected {expected})"
    print(f"{d}: DOY={got} {status}")
