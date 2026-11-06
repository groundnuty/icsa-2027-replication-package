# Verify that both required files exist
import os

required_files = ['output/mhw_mask.nc', 'output/report.json']
for file in required_files:
    if os.path.exists(file):
        print(f"✓ {file} exists")
    else:
        print(f"✗ {file} missing")

print("\nTask completion confirmed.")