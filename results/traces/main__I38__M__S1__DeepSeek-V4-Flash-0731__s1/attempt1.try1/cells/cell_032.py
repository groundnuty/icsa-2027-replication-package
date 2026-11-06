
import numpy as np
from datetime import date
import json

intermediate_dir = 'intermediate'

# Load metadata and data
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)
target_dates = [date.fromisoformat(d) for d in meta['target_dates']]

threshold_smooth = np.load(f'{intermediate_dir}/threshold_smooth.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

target_doy = [day_of_year(d) for d in target_dates]
n_days = len(target_dates)

# Compute hot
hot = np.zeros((n_days, 60, 60), dtype=bool)
for i in range(n_days):
    doy = target_doy[i]
    sst = target_sst[i].astype(np.float64)
    th = threshold_smooth[doy - 1]
    hot[i] = (sst >= th) & ~np.isnan(sst)

# For each sea cell, find cells that are in MHWs on day 43
# MHW definition: run of >= 5 consecutive hot days, joined if separated by 1-2 cold days

# Let me check: for each sea cell, what is the MHW status on day 43?
# I'll compute the MHW mask and check

mhw_mask = np.zeros((n_days, 60, 60), dtype=np.uint8)
for la in range(60):
    for lo in range(60):
        if not sea_cells[la, lo]:
            continue
        cell_hot = hot[:, la, lo]
        
        runs = []
        i = 0
        while i < n_days:
            if cell_hot[i]:
                start = i
                while i < n_days and cell_hot[i]:
                    i += 1
                end = i - 1
                runs.append((start, end))
            else:
                i += 1
        
        mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        if mhws:
            merged = [mhws[0]]
            for m in mhws[1:]:
                gap = m[0] - merged[-1][1] - 1
                if gap <= 2:
                    merged[-1] = (merged[-1][0], m[1])
                else:
                    merged.append(m)
            
            for start, end in merged:
                mhw_mask[start:end+1, la, lo] = 1

# Check which cells are in MHWs on day 43
cells_in_mhw_43 = np.argwhere(mhw_mask[43] == 1)
print(f"Cells in MHW on day 43: {len(cells_in_mhw_43)}")

if len(cells_in_mhw_43) > 0:
    for la, lo in cells_in_mhw_43[:3]:
        print(f"\nCell ({la}, {lo}):")
        # Show hot pattern from day 38 to day 50
        print(f"  Hot days 38-50: {[bool(hot[i, la, lo]) for i in range(38, 51)]}")
        # Show MHW status
        print(f"  MHW days 38-50: {[bool(mhw_mask[i, la, lo]) for i in range(38, 51)]}")
