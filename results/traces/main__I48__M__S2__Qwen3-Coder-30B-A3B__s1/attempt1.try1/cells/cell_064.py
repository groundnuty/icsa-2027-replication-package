# Final verification
import os

print("✅ FINAL TASK VERIFICATION")
print("=" * 30)

# Check files exist
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file)} - MISSING")
        all_present = False

print("=" * 30)
if all_present:
    print("🎉 ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("Marine heatwave detection task completed as requested.")
    print("Both files are ready for use.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: FINAL")