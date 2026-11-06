# Final status check
import os

status = {
    "mhw_mask.nc": os.path.exists("output/mhw_mask.nc"),
    "report.json": os.path.exists("output/report.json")
}

print("FINAL STATUS:")
for file, exists in status.items():
    print(f"  {file}: {'✓ FOUND' if exists else '✗ MISSING'}")

print(f"\nTASK STATUS: {'COMPLETE' if all(status.values()) else 'INCOMPLETE'}")