
import numpy as np
import datetime as dt

def day_of_year(ts):
    d = dt.datetime.fromtimestamp(ts.astype('datetime64[ns]').astype(np.int64) / 1e9, tz=dt.timezone.utc)
    year = d.year
    month = d.month
    day = d.day
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month > 2:
        std_doy += 1
    return std_doy

# Verify day-of-year for key dates
check_dates = [
    np.datetime64('2007-06-01'),
    np.datetime64('2007-06-30'),
    np.datetime64('2007-07-01'),
    np.datetime64('2007-08-01'),
    np.datetime64('2007-08-31'),
    np.datetime64('1992-02-28'),
    np.datetime64('1992-02-29'),
    np.datetime64('1992-03-01'),
    np.datetime64('1992-12-31'),
    np.datetime64('1993-02-28'),
    np.datetime64('1993-03-01'),
    np.datetime64('1993-12-31'),
]

print("Date         | Day of year")
for d in check_dates:
    print(f"{str(d)[:10]} | {day_of_year(d)}")

# Verify the tgt_doy values
tgt_times = np.load('/tmp/tgt_times.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')
print(f"\nTarget DOY range: {tgt_doy.min()} to {tgt_doy.max()}")
print(f"First target date: {str(tgt_times[0])[:10]}, doy = {tgt_doy[0]}")
print(f"Last target date: {str(tgt_times[-1])[:10]}, doy = {tgt_doy[-1]}")

# Verify 2007 is not a leap year
# so June 1 = day 153 and Aug 31 = day 244
assert tgt_doy[0] == 153, f"Expected doy 153 for June 1, got {tgt_doy[0]}"
assert tgt_doy[-1] == 244, f"Expected doy 244 for Aug 31, got {tgt_doy[-1]}"
print("Target day-of-year mapping verified: correct")
