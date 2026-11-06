
import datetime

def date_to_doy(dt):
    """Map date to day of year 1-366, fixed mapping where Feb always has 29 days.
    1 Jan=1, 28 Feb=59, 29 Feb=60 (leap only), 1 Mar=61, ..., 31 Dec=366."""
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

# Test
for d in [datetime.date(1992,1,1), datetime.date(1992,2,28), datetime.date(1992,2,29), datetime.date(1992,3,1), datetime.date(1993,2,28), datetime.date(1993,3,1), datetime.date(2019,12,31), datetime.date(1992,12,31), datetime.date(1993,12,31)]:
    print(d, "->", date_to_doy(d))
