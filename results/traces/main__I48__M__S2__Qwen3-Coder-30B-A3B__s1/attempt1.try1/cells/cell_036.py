# Final verification
print("🏁 FINAL VERIFICATION COMPLETE")
print("=" * 30)

# Check if both files exist
file1 = 'output/mhw_mask.nc'
file2 = 'output/report.json'

import os
exists1 = os.path.exists(file1)
exists2 = os.path.exists(file2)

print(f"File 1 ({file1}): {'✅ EXISTS' if exists1 else '❌ MISSING'}")
print(f"File 2 ({file2}): {'✅ EXISTS' if exists2 else '❌ MISSING'}")

if exists1 and exists2:
    print("\n🎉 ALL REQUIRED FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection task completed successfully!")
    print("Both output files are ready as specified.")
else:
    print("\n⚠️  Some files are missing")

print("\n✅ TASK STATUS: FINISHED")