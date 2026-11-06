
# Check if the data variables from the previous run are still available
try:
    print("per_cell_mhw shape:", per_cell_mhw.shape)
    print("events:", events)
    print("target_dates:", target_dates[:5], "...", target_dates[-5:])
except NameError as e:
    print("Not available:", e)
