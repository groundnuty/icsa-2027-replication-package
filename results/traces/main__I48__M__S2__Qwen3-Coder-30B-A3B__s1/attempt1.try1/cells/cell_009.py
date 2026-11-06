# Verify final file existence
import os

files_exist = []
for filename in ['output/mhw_mask.nc', 'output/report.json']:
    exists = os.path.exists(filename)
    files_exist.append((filename, exists))
    print(f"{filename}: {'Exists' if exists else 'Missing'}")

if all(exists for _, exists in files_exist):
    print("\n✅ Both required files have been successfully created!")
else:
    print("\n❌ Some files are missing.")