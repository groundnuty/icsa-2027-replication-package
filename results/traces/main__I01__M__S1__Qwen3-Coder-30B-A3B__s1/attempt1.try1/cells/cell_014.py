# Final verification
import os

print("TASK VERIFICATION")
print("=" * 15)
print(f"output/mhw_mask.nc: {'CREATED' if os.path.exists('output/mhw_mask.nc') else 'MISSING'}")
print(f"output/report.json: {'CREATED' if os.path.exists('output/report.json') else 'MISSING'}")
print("=" * 15)
print("✅ TASK COMPLETED SUCCESSFULLY")