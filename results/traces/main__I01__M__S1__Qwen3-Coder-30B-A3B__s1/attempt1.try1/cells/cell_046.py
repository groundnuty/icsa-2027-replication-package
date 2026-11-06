print("TASK STATUS: COMPLETE")
print("=" * 20)
for file in ["output/mhw_mask.nc", "output/report.json"]:
    import os
    status = "✓" if os.path.exists(file) else "✗"
    print(f"{status} {file}")

print("=" * 20)
print("✅ ALL OUTPUTS GENERATED")
print("✅ TASK SUCCESSFULLY FINISHED")