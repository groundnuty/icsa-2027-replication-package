
import datetime

def day_of_year(d):
    doy = (d - datetime.date(d.year, 1, 1)).days + 1
    is_leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    if not is_leap and d.month >= 3:
        doy += 1
    return doy

# Verify
print("2021-01-01:", day_of_year(datetime.date(2021, 1, 1)))
print("2021-02-28:", day_of_year(datetime.date(2021, 2, 28)))
print("2021-03-01:", day_of_year(datetime.date(2021, 3, 1)))
print("2021-12-31:", day_of_year(datetime.date(2021, 12, 31)))
print("2020-02-29:", day_of_year(datetime.date(2020, 2, 29)))
print("2020-03-01:", day_of_year(datetime.date(2020, 3, 1)))
print("1992-03-01:", day_of_year(datetime.date(1992, 3, 1)))
print("1993-03-01:", day_of_year(datetime.date(1993, 3, 1)))
print("1992-12-31:", day_of_year(datetime.date(1992, 12, 31)))
print("1993-12-31:", day_of_year(datetime.date(1993, 12, 31)))
