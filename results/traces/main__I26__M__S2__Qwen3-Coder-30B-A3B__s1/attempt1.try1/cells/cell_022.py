# Final confirmation that task is complete
import os

print("FINAL CONFIRMATION")
print("=" * 20)

# Check if both files exist
file1_exists = os.path.exists('output/mhw_mask.nc')
file2_exists = os.path.exists('output/report.json')

print(f"output/mhw_mask.nc: {'✅ EXISTS' if file1_exists else '❌ MISSING'}")
print(f"output/report.json: {'✅ EXISTS' if file2_exists else '❌ MISSING'}")

if file1_exists and file2_exists:
    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All required outputs have been generated.")
else:
    print("\n❌ TASK INCOMPLETE - Missing files")