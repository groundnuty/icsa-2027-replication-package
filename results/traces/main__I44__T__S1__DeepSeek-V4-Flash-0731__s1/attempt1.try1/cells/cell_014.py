import datetime as dt

def day_of_year(date):
    """Map date to day of year 1-366.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60.
    """
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    
    # In non-leap years, add 1 to days after Feb 28 (i.e., day 60 is skipped)
    # Actually, let me reconsider. The mapping says:
    # 28 Feb = 59, 1 Mar = 61 (non-leap), 29 Feb = 60, 1 Mar = 61 (leap)
    # So in non-leap years: Feb has 28 days, and after day 59, we go to 61.
    # In leap years: Feb has 29 days, 29 Feb = 60, then 61 for Mar 1.
    
    # So the mapping is NOT the standard day-of-year. It's:
    # Standard DOY for Jan and Feb (up to 59)
    # In leap years: 29 Feb = 60 (same as standard DOY)
    # After Feb: day = standard_DOY + 1 for non-leap years (because day 60 is skipped)
    # After Feb: day = standard_DOY for leap years
    
    if not is_leap and date.month >= 3:
        doy += 1
    
    return doy

# Test
print(day_of_year(dt.date(1992, 1, 1)))   # 1 (leap)
print(day_of_year(dt.date(1992, 2, 28)))  # 59 (leap)
print(day_of_year(dt.date(1992, 2, 29)))  # 60 (leap)
print(day_of_year(dt.date(1992, 3, 1)))   # 61 (leap)
print(day_of_year(dt.date(1992, 12, 31))) # 366 (leap)
print(day_of_year(dt.date(1993, 1, 1)))   # 1
print(day_of_year(dt.date(1993, 2, 28)))  # 59
print(day_of_year(dt.date(1993, 3, 1)))   # 61
print(day_of_year(dt.date(1993, 12, 31))) # 366
print(day_of_year(dt.date(1993, 3, 2)))   # 62
print(day_of_year(dt.date(1993, 2, 27)))  # 58
