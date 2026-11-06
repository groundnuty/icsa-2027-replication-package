
from datetime import date

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return cum_days[month - 1] + day

# Check
d = date(1992, 12, 31)
print('Dec 31 1992 DOY:', day_of_year(d))
d = date(1992, 12, 30)
print('Dec 30 1992 DOY:', day_of_year(d))
d = date(1993, 12, 31)
print('Dec 31 1993 DOY:', day_of_year(d))
d = date(1992, 3, 1)
print('Mar 1 1992 DOY:', day_of_year(d))

# Check cum_days for December
cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
print('cum_days[11] =', cum_days[11])  # December
print('DOY for Dec 31:', 334 + 31)  # Should be 365?
