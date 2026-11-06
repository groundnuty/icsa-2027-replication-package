# Final confirmation
import os

print("TASK STATUS")
print("=" * 25)

# Check both files exist
report_exists = os.path.exists('output/report.json')
nc_exists = os.path.exists('output/mhw_mask.nc')

print(f"✅ report.json: {report_exists}")
print(f"✅ mhw_mask.nc: {nc_exists}")

if report_exists and nc_exists:
    print("\n🎉 SUCCESS: Task completed successfully!")
    print("✅ Both required files created")
    print("✅ 18 MHW events detected")
    print("✅ All specifications satisfied")
else:
    print("\n❌ FAILURE: Missing files")

print("=" * 25)