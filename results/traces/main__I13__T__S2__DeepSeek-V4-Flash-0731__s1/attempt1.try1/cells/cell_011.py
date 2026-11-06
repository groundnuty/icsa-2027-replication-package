
import numpy as np
import datetime

def date_to_doy(dates):
    """Convert dates to day-of-year index (1-366) using the specified mapping."""
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

# Test
test_dates = np.array([
    np.datetime64('1992-01-01'),
    np.datetime64('1992-02-28'),
    np.datetime64('1992-02-29'),
    np.datetime64('1992-03-01'),
    np.datetime64('1992-03-05'),
    np.datetime64('1992-12-31'),
    np.datetime64('1991-12-27'),
    np.datetime64('2003-01-05'),
    np.datetime64('2021-06-01'),
    np.datetime64('2021-08-31'),
])
print(date_to_doy(test_dates))
# Expected: 1, 59, 60, 61, 65, 366, 361, 5, 152, 243
