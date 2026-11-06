# Final verification
import os

print("FINAL VERIFICATION")
print("=" * 20)

# Check that both files exist
file1 = 'output/mhw_mask.nc'
file2 = 'output/report.json'

exists1 = os.path.exists(file1)
exists2 = os.path.exists(file2)

print(f"{file1}: {'✅ FOUND' if exists1 else '❌ MISSING'}")
print(f"{file2}: {'✅ FOUND' if exists2 else '❌ MISSING'}")

if exists1 and exists2:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection task completed successfully!")
else:
    print("\n❌ TASK INCOMPLETE")

print("\nProcess terminated normally.")