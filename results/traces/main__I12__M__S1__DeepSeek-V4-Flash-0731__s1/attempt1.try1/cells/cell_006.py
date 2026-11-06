
from datetime import date, timedelta

# Baseline window
start = date(1991, 12, 27)
end = date(2003, 1, 5)
count = 0
d = start
while d <= end:
    count += 1
    d += timedelta(days=1)
print("Baseline window days:", count)

# Target period
start = date(2009, 6, 1)
end = date(2009, 8, 31)
count = 0
d = start
while d <= end:
    count += 1
    d += timedelta(days=1)
print("Target days:", count)

# Total baseline years 1992-2002
count = 0
for y in range(1992, 2003):
    if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
        count += 366
    else:
        count += 365
print("Baseline years total days:", count)
