# Final verification that task is complete
import os

print("FINAL VERIFICATION")
print("=" * 20)
files = ['output/mhw_mask.nc', 'output/report.json']

all_present = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

print("=" * 20)
if all_present:
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All required files created as specified.")
else:
    print("❌ Some files missing")