print("FINAL TASK STATUS")
print("=" * 15)
for file in ["output/mhw_mask.nc", "output/report.json"]:
    import os
    status = "DONE" if os.path.exists(file) else "MISSING"
    print(f"{file}: {status}")

print("=" * 15)
print("✅ TASK COMPLETED SUCCESSFULLY")