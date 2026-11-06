# Verify all files exist
import os

files = [
    'output/report.json',
    'output/mhw_mask.nc', 
    'output/thresholds.npy',
    'output/climatologies.npy'
]

print("Final verification of created files:")
all_good = True
for file in files:
    exists = os.path.exists(file)
    print(f"  {file}: {'✓' if exists else '✗'}")
    if not exists:
        all_good = False

if all_good:
    print("\n🎉 All required files successfully created!")
    print("Task completion confirmed.")
else:
    print("\n❌ Some files missing.")