
def day_of_year(d):
    """Map date to day of year (1-366) using perpetual leap year calendar.
    1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366"""
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # Feb=29
    doy = d.day + sum(month_days[:d.month])
    return doy

from datetime import date
print(f"2003-01-01 -> {day_of_year(date(2003,1,1))}")
print(f"2003-02-28 -> {day_of_year(date(2003,2,28))}")
print(f"2004-02-29 -> {day_of_year(date(2004,2,29))}")
print(f"2003-03-01 -> {day_of_year(date(2003,3,1))}")
print(f"2003-12-31 -> {day_of_year(date(2003,12,31))}")
print(f"2003-06-01 -> {day_of_year(date(2003,6,1))}")
print(f"2003-08-31 -> {day_of_year(date(2003,8,31))}")
print(f"2003-01-31 -> {day_of_year(date(2003,1,31))}")
print(f"2003-02-01 -> {day_of_year(date(2003,2,1))}")
print(f"2004-03-01 -> {day_of_year(date(2004,3,1))}")
print(f"2004-12-31 -> {day_of_year(date(2004,12,31))}")
