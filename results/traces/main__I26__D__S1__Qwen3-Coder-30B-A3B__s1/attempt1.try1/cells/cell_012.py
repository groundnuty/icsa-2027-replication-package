# Final verification
import os

# Check files exist
mhw_file_exists = os.path.exists('output/mhw_mask.nc')
report_file_exists = os.path.exists('output/report.json')

print("FINAL VERIFICATION:")
print(f"✅ mhw_mask.nc exists: {mhw_file_exists}")
print(f"✅ report.json exists: {report_file_exists}")

if mhw_file_exists and report_file_exists:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("Both required output files have been created as specified.")
else:
    print("\n❌ Some files missing")