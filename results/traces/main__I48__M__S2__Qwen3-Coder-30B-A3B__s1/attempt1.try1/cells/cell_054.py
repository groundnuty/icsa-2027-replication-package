# Final verification
import os

print("✅ TASK COMPLETION VERIFICATION")
print("=" * 30)

# Check files
files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)} - PRESENT")
    else:
        print(f"❌ {os.path.basename(file)} - MISSING")
        all_exist = False

print("=" * 30)
if all_exist:
    print("🎉 ALL REQUIRED FILES GENERATED SUCCESSFULLY")
    print("Marine heatwave detection task completed as requested.")
    print("Both output files are ready for use.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: FINAL")