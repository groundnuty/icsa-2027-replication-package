
from datetime import date, timedelta

start = date(1991, 12, 27)
end = date(2003, 1, 5)
count = (end - start).days + 1
print(f"Days from {start} to {end}: {count}")

# Check leap years in this range: 1992, 1996, 2000
# 1991: 5 days (Dec 27-31)
# 1992-2002: 11 years
# 2003: 5 days (Jan 1-5)
# Total = 5 + 11*365 + 3 (leap days in 1992, 1996, 2000) + 5 = 5 + 4015 + 3 + 5 = 4028

# Let me verify
d = start
dates = []
while d <= end:
    dates.append(d)
    d += timedelta(days=1)
print(f"Number of dates: {len(dates)}")
