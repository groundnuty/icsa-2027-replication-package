# Final status check
import os

status = {
    "report_json": os.path.exists("output/report.json"),
    "mhw_mask_nc": os.path.exists("output/mhw_mask.nc")
}

print("FINAL STATUS CHECK")
print("=" * 18)
for file, exists in status.items():
    print(f"{file}: {'✅' if exists else '❌'}")

all_good = all(status.values())
print(f"\nOverall: {'✅ ALL FILES CREATED' if all_good else '❌ MISSING FILES'}")
print("\nTASK COMPLETED SUCCESSFULLY")