
def day_of_year(month, day):
    """Map month and day to day of year 1-366 using fixed mapping."""
    # Cumulative days before each month (non-leap) + 1 for months after Feb for leap
    # But we're using the fixed mapping from the spec, so:
    # Jan = 1-31
    # Feb = 32-59 (28 Feb = 59)
    # Feb 29 = 60
    # Mar = 61-91
    # etc.
    
    # Using fixed mapping by month and day
    month_start = {
        1: 1,
        2: 32,
        3: 61,  # March starts at 61
        4: 92,
        5: 122,
        6: 153,
        7: 183,
        8: 214,
        9: 245,
        10: 275,
        11: 306,
        12: 336,
    }
    return month_start[month] + day - 1

# Test
print("Jan 1:", day_of_year(1, 1))
print("Jan 31:", day_of_year(1, 31))
print("Feb 1:", day_of_year(2, 1))
print("Feb 28:", day_of_year(2, 28))
print("Feb 29:", day_of_year(2, 29))
print("Mar 1:", day_of_year(3, 1))
print("Dec 31:", day_of_year(12, 31))
