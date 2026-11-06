
import numpy as np

def date_to_doy(dates):
    """Convert dates to day-of-year index (1-366) using the specified mapping.
    Month offsets: Jan=0, Feb=31, Mar=60, Apr=91, May=121, Jun=152, Jul=182,
    Aug=213, Sep=244, Oct=274, Nov=305, Dec=335
    """
    dates = np.asarray(dates)
    # Extract month and day
    months = (dates.astype('datetime64[M]').astype(np.int64) % 12) + 1
    days = (dates.astype('datetime64[D]').astype(np.int64) - 
            dates.astype('datetime64[M]').astype(np.int64)) + 1
    
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doy = month_offsets[months - 1] + days
    return doy

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
