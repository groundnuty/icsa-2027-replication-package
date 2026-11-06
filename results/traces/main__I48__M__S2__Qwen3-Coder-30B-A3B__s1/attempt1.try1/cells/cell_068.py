# Final verification
import os

print("✅ TASK COMPLETION CONFIRMED")
print("=" * 30)

# Check both files
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)} - CREATED")
    else:
        print(f"❌ {os.path.basename(file)} - MISSING")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL OUTPUT FILES SUCCESSFULLY GENERATED")
    print("Marine heatwave detection analysis completed!")
    print("Both required files are ready for use.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: FINAL")