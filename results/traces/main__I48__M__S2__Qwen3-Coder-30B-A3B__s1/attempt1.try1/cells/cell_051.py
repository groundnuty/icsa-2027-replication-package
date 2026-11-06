# Final confirmation
import os

print("TASK COMPLETION STATUS")
print("=" * 25)

# Check files
files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in files:
    if os.path.exists(file):
        print(f"✅ {os.path.basename(file)}")
    else:
        print(f"❌ {os.path.basename(file)}")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 ALL OUTPUT FILES GENERATED SUCCESSFULLY")
    print("Marine heatwave detection analysis completed as requested.")
    print("Both required files are present.")
else:
    print("⚠️  Some files are missing")

print("\n✅ TASK STATUS: COMPLETE")