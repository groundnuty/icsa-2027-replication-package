
import datetime

baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)

# Baseline period proper
proper_start = datetime.date(1992, 1, 1)
proper_end = datetime.date(2002, 12, 31)

all_dates = []
d = baseline_start
while d <= baseline_end:
    all_dates.append(d)
    d += datetime.timedelta(days=1)

# Indices of proper baseline dates
proper_indices = [i for i, d in enumerate(all_dates) if proper_start <= d <= proper_end]
print(f"Proper baseline indices: {proper_indices[0]} to {proper_indices[-1]}, count = {len(proper_indices)}")
print(f"Total dates: {len(all_dates)}")
print(f"Extension at start: {proper_indices[0]} dates")
print(f"Extension at end: {len(all_dates) - proper_indices[-1] - 1} dates")
print(f"First few proper dates: {all_dates[proper_indices[0]]} to {all_dates[proper_indices[2]]}")
print(f"Last few proper dates: {all_dates[proper_indices[-3]]} to {all_dates[proper_indices[-1]]}")
