
import numpy as np
import datetime

def day_of_year(dt):
    """Map date to day of year 1-366.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60."""
    month = dt.month
    day = dt.day
    # Days before each month, as if Feb has 29 days (i.e., always leap-year counting)
    # This means: Jan=1-31, Feb=32-60, Mar=61-91, Apr=92-121, May=122-152, 
    # Jun=153-182, Jul=183-213, Aug=214-244, Sep=245-274, Oct=275-305,
    # Nov=306-335, Dec=336-366
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Test
print(f"1 Jan 1992: doy = {day_of_year(datetime.date(1992,1,1))}")
print(f"28 Feb 1992: doy = {day_of_year(datetime.date(1992,2,28))}")
print(f"29 Feb 1992: doy = {day_of_year(datetime.date(1992,2,29))}")
print(f"1 Mar 1992: doy = {day_of_year(datetime.date(1992,3,1))}")
print(f"1 Mar 1993: doy = {day_of_year(datetime.date(1993,3,1))}")
print(f"31 Dec 1992: doy = {day_of_year(datetime.date(1992,12,31))}")
print(f"31 Dec 1993: doy = {day_of_year(datetime.date(1993,12,31))}")
print(f"28 Feb 1993: doy = {day_of_year(datetime.date(1993,2,28))}")
print(f"30 Jun 2009: doy = {day_of_year(datetime.date(2009,6,30))}")
print(f"1 Jun 2009: doy = {day_of_year(datetime.date(2009,6,1))}")
