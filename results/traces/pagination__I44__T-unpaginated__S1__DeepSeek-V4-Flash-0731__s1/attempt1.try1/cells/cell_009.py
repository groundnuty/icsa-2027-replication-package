from datetime import date, timedelta

# Build a mapping of date -> day-of-year
# The day-of-year mapping follows the leap-year calendar convention

def month_day_to_doy(month, day):
    """Map month/day to day-of-year 1-366 using leap-year convention."""
    # Days in each month (leap year)
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Test
print(month_day_to_doy(1, 1))    # 1
print(month_day_to_doy(2, 28))   # 59
print(month_day_to_doy(2, 29))   # 60
print(month_day_to_doy(3, 1))    # 61
print(month_day_to_doy(12, 31))  # 366
print(month_day_to_doy(6, 1))    # 153
print(month_day_to_doy(8, 31))   # 244

def date_to_doy(d):
    """Get day-of-year for a date using month/day mapping (not tm_yday)."""
    return month_day_to_doy(d.month, d.day)
