
def date_to_doy(d):
    """Map date to day of year 1-366 using the task's mapping.
    Always counts Feb as having 29 days in cumulative sum."""
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

# Test
import datetime
tests = [
    (datetime.date(2007,1,1), 1),
    (datetime.date(2007,2,28), 59),
    (datetime.date(2007,3,1), 61),
    (datetime.date(2007,12,31), 366),
    (datetime.date(2008,2,29), 60),
    (datetime.date(2008,3,1), 61),
    (datetime.date(2008,2,28), 59),
    (datetime.date(1992,3,1), 61),
    (datetime.date(1996,2,29), 60),
]
for d, expected in tests:
    got = date_to_doy(d)
    status = "OK" if got == expected else f"FAIL (expected {expected})"
    print(f"{d}: doy={got} {status}")
