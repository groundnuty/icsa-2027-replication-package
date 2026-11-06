from datetime import date, timedelta

start = date(1991, 12, 27)
end = date(2003, 1, 5)
current = start
count = 0
dates = []
while current <= end:
    dates.append(current)
    count += 1
    current += timedelta(days=1)

print(f"Number of dates: {count}")
print(f"First: {dates[0]}, Last: {dates[-1]}")
