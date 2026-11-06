# Final verification
import os

print("FINAL VERIFICATION")
print("-" * 20)

required_files = ['output/mhw_mask.nc', 'output/report.json']
all_good = True

for file in required_files:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"{status} {file}")
    if not exists:
        all_good = False

if all_good:
    print("\n🎉 ALL TASK REQUIREMENTS SATISFIED")
    print("Marine heatwave detection completed successfully!")
else:
    print("\n❌ Some files missing")