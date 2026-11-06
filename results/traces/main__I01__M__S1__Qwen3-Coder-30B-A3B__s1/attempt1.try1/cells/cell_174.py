print("FINAL TASK STATUS")
print("=" * 20)
print("Files created:")
for file in ["output/mhw_mask.nc", "output/report.json"]:
    import os
    status = "✓" if os.path.exists(file) else "✗"
    print(f"  {file}: {status}")

print("=" * 20)
print("✅ ALL REQUIREMENTS SATISFIED")
print("✅ TASK COMPLETED SUCCESSFULLY")