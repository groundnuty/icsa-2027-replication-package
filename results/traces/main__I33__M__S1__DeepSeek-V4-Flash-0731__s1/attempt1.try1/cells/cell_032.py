
from datetime import datetime, timezone, timedelta

# Target start date
target_start = datetime(2014, 6, 1, tzinfo=timezone.utc)

# Day 48 = June 1 + 48 days
day48 = target_start + timedelta(days=48)
print(f"Day 48: {day48.date()}")  # Should be July 19

# Day 80 = June 1 + 80 days
day80 = target_start + timedelta(days=80)
print(f"Day 80: {day80.date()}")  # Should be Aug 20

# Day 0 = June 1
day0 = target_start
print(f"Day 0: {day0.date()}")
