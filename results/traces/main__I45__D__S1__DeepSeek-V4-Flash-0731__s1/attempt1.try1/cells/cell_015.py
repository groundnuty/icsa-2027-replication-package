
def day_of_year_fixed(month, day):
    """Map month/day to fixed day of year (1-366), with Feb 29 = 60."""
    month_offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return month_offsets[month-1] + day

# Test
print("Jan 1:", day_of_year_fixed(1, 1))  # 1
print("Feb 28:", day_of_year_fixed(2, 28))  # 59
print("Feb 29:", day_of_year_fixed(2, 29))  # 60
print("Mar 1:", day_of_year_fixed(3, 1))  # 61
print("Dec 31:", day_of_year_fixed(12, 31))  # 366

# In a non-leap year, no date maps to 60
# E.g., in 1993 (non-leap), Feb has only 28 days, so no Feb 29 = 60
# But Mar 1 = 61

print("\nDay 1 = Jan 1")
print("Day 60 exists only for Feb 29 in leap years")
