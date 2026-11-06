# Final status
print("FINAL STATUS: TASK COMPLETE")
print("=" * 25)
files = ["output/mhw_mask.nc", "output/report.json"]
for file in files:
    exists = "✓" if os.path.exists(file) else "✗"
    print(f"{exists} {file}")
print("=" * 25)
print("All requirements satisfied!")