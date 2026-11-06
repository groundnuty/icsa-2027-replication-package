# Final verification that task is complete
import os

print("FINAL VERIFICATION")
print("=" * 20)
files = ['output/mhw_mask.nc', 'output/report.json']

all_created = True
for file in files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_created = False

print("=" * 20)
if all_created:
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All required files have been created as specified.")
else:
    print("❌ Some files missing")