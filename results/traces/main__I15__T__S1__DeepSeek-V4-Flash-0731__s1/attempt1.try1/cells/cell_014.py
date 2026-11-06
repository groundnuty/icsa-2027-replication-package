import numpy as np
from datetime import datetime, timedelta

# Get the dates for the extended baseline indices
def np64_to_date(ts):
    dt = datetime.utcfromtimestamp(ts.astype('datetime64[us]').astype(np.int64) / 1e6)
    return dt

# Build date arrays for extended baseline
b_dates = []
for i in range(len(b_idx)):
    dt = np64_to_date(t_vals[b_idx[i]])
    b_dates.append(dt)

# Baseline core dates: 1992-01-01 to 2002-12-31
base_core_start = datetime(1992, 1, 1)
base_core_end = datetime(2002, 12, 31)

# For each date T in extended baseline, find which baseline dates B (1992-2002)
# are within ±5 calendar days, and what doy those B have.
# Then T belongs to the pool of doy(B) for each such B.

# Build a list of (date, doy) for all baseline core dates
core_dates = []
for dt in b_dates:
    if base_core_start <= dt <= base_core_end:
        core_dates.append((dt, date_to_doy(dt.year, dt.month, dt.day)))

print(f"Core baseline dates: {len(core_dates)}")
print(f"First core: {core_dates[0]}")
print(f"Last core: {core_dates[-1]}")

# For each date T in extended baseline, determine pool memberships
# T belongs to pool d if there exists a core baseline date B with doy(B)=d and |T-B|<=5 days

# Build a mapping: for each doy d (1-366, d≠60), list of date indices in extended baseline
pools = {d: [] for d in range(1, 367) if d != 60}

for t_idx_local, dt in enumerate(b_dates):
    # Check which core baseline dates are within ±5 days of dt
    for b_dt, b_doy in core_dates:
        if b_doy == 60:
            continue  # day 60 gets no pool of its own
        delta = abs((dt - b_dt).days)
        if delta <= 5:
            pools[b_doy].append(t_idx_local)
    # break after first few for testing

# Convert to unique lists
for d in pools:
    pools[d] = sorted(set(pools[d]))

# Check some pools
for d in [1, 59, 61, 180, 365]:
    dates_in_pool = [b_dates[i] for i in pools[d]]
    print(f"\nPool doy {d}: {len(dates_in_pool)} dates")
    if len(dates_in_pool) > 0:
        print(f"  First: {dates_in_pool[0]}")
        print(f"  Last: {dates_in_pool[-1]}")
