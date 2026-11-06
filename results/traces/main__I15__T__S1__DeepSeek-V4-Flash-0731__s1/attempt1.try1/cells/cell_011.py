import numpy as np

def date_to_doy(year, month, day):
    """Convert date to day of year (1-366). Non-leap years have no day 60."""
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    
    # Days before each month (in leap year terms)
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    cum_days_nonleap = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    
    cum = cum_days_leap if is_leap else cum_days_nonleap
    return cum[month-1] + day

# Test
test_cases = [
    (1992, 1, 1, 1),
    (1992, 2, 28, 59),
    (1992, 2, 29, 60),
    (1992, 3, 1, 61),
    (1992, 12, 31, 366),
    (1993, 1, 1, 1),
    (1993, 2, 28, 59),
    (1993, 3, 1, 61),  # Non-leap: day 61, day 60 doesn't exist
    (1993, 12, 31, 365),
    (1996, 2, 29, 60),  # 1996 is leap
    (2000, 2, 29, 60),  # 2000 is leap
    (2001, 3, 1, 61),
]

for y, m, d, expected in test_cases:
    result = date_to_doy(y, m, d)
    ok = "OK" if result == expected else "FAIL"
    print(f"{y}-{m:02d}-{d:02d} -> doy {result} (expected {expected}) {ok}")
