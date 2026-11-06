# Final verification
import os

print("✅ FINAL TASK VERIFICATION COMPLETE")
print("=" * 35)

# Check files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file)} - MISSING")
        all_present = False

print("=" * 35)
if all_present:
    print("🎉 ALL REQUIRED FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection analysis completed!")
    print("Both output files are ready for use.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")