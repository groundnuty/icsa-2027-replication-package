# Final verification that both files exist
import os

files_exist = []
for filename in ['output/mhw_mask.nc', 'output/report.json']:
    exists = os.path.exists(filename)
    files_exist.append((filename, exists))
    print(f"{filename}: {'✓ EXISTS' if exists else '✗ MISSING'}")

if all(exists for _, exists in files_exist):
    print("\n✅ Both required files have been successfully generated!")
else:
    print("\n❌ Some files are missing!")