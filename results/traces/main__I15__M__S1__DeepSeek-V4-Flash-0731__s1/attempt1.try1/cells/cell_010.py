from datetime import datetime

def day_of_year(date):
    """Map date to day of year 1-366 by month and day."""
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# Test
print("1 Jan:", day_of_year(datetime(1992, 1, 1)))  # 1
print("28 Feb 1992:", day_of_year(datetime(1992, 2, 28)))  # 59
print("29 Feb 1992:", day_of_year(datetime(1992, 2, 29)))  # 60
print("1 Mar 1992:", day_of_year(datetime(1992, 3, 1)))  # 61
print("28 Feb 1993:", day_of_year(datetime(1993, 2, 28)))  # 59
print("1 Mar 1993:", day_of_year(datetime(1993, 3, 1)))  # 61
print("31 Dec 1992:", day_of_year(datetime(1992, 12, 31)))  # 366
print("31 Dec 1993:", day_of_year(datetime(1993, 12, 31)))  # 366
print("1 Mar 2000:", day_of_year(datetime(2000, 3, 1)))  # 61
print("29 Feb 2000:", day_of_year(datetime(2000, 2, 29)))  # 60
print("1 Jan 1992:", day_of_year(datetime(1992, 1, 1)))  # 1
print("31 Jan:", day_of_year(datetime(1992, 1, 31)))  # 31
print("1 Feb:", day_of_year(datetime(1992, 2, 1)))  # 32
print("31 Dec:", day_of_year(datetime(1992, 12, 31)))  # 366
print("31 Mar:", day_of_year(datetime(1992, 3, 31)))  # 91
print("1 Apr:", day_of_year(datetime(1992, 4, 1)))  # 92
