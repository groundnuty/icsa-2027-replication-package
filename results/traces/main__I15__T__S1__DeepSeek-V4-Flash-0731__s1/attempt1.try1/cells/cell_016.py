import numpy as np
from datetime import datetime, timedelta

# Build pools for each doy (1-366, d≠60)
pools = {d: set() for d in range(1, 367) if d != 60}

# For each core baseline date, mark all extended baseline dates within ±5 days
for b_dt, b_doy in core_dates:
    if b_doy == 60:
        continue  # Day 60 gets no pool of its own
    
    # Find all dates within ±5 calendar days
    for delta in range(-5, 6):
        t = b_dt + timedelta(days=delta)
        if t in date_to_idx:
            pools[b_doy].add(date_to_idx[t])

# Convert sets to sorted lists
for d in pools:
    pools[d] = sorted(pools[d])

# Verify pool sizes
print("Pool sizes for sample doys:")
for d in [1, 59, 61, 180, 365, 100, 200]:
    print(f"  doy {d}: {len(pools[d])} dates")

# Check if all doys have pools
for d in range(1, 367):
    if d != 60:
        if len(pools[d]) == 0:
            print(f"  WARNING: doy {d} has empty pool!")

print("\nAll pools have data" if all(len(pools[d]) > 0 for d in pools) else "Some pools are empty!")

# Verify a specific pool
# doy 1 = Jan 1, so pool should include dates from Dec 27 to Jan 6 around each Jan 1 of 1992-2002
dates_d1 = [b_dates[i] for i in pools[1]]
print(f"\nDoy 1 pool dates: {dates_d1[:5]} ... {dates_d1[-5:]}")
print(f"Doy 1 pool count: {len(dates_d1)}")
