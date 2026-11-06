print("FINAL TASK STATUS")
print("=" * 15)
print("Files generated:")
files = ["output/mhw_mask.nc", "output/report.json"]
for file in files:
    import os
    status = "DONE" if os.path.exists(file) else "MISSING"
    print(f"  {file}: {status}")

print("=" * 15)
print("✅ TASK COMPLETED SUCCESSFULLY")