# Verify the final output files exist
import os

files_exist = []
for filename in ['output/mhw_mask.nc', 'output/report.json']:
    exists = os.path.exists(filename)
    files_exist.append((filename, exists))
    print(f"{filename}: {'✓' if exists else '✗'}")

if all(exists for _, exists in files_exist):
    print("\n✅ Both output files have been successfully created!")
else:
    print("\n❌ Some output files are missing.")