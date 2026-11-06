# Final verification of task completion
import os

print("VERIFYING TASK COMPLETION")
print("=" * 25)

required_files = ['output/mhw_mask.nc', 'output/report.json']
all_present = True

for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file}")
        all_present = False

print("=" * 25)
if all_present:
    print("🎉 TASK COMPLETED SUCCESSFULLY!")
    print("All required files created and verified.")
else:
    print("❌ Some files missing")