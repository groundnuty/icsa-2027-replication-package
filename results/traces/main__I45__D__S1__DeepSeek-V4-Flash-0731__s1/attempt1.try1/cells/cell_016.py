
def day_of_year_fixed(month, day):
    """Map month/day to fixed day of year (1-366), assuming leap-year offsets."""
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[month-1] + day

# Test
print("Jan 1:", day_of_year_fixed(1, 1))  # 1
print("Feb 28:", day_of_year_fixed(2, 28))  # 59
print("Feb 29:", day_of_year_fixed(2, 29))  # 60
print("Mar 1:", day_of_year_fixed(3, 1))  # 61
print("Dec 31:", day_of_year_fixed(12, 31))  # 366
print("Jun 1:", day_of_year_fixed(6, 1))  # 152+1 = 153
print("Aug 31:", day_of_year_fixed(8, 31))  # 213+31 = 244
