# Final verification that both files exist
import os

files = ['output/mhw_mask.nc', 'output/report.json']
all_exist = True

print("FINAL VERIFICATION")
print("-" * 20)
for file in files:
    exists = os.path.exists(file)
    print(f"{'✓' if exists else '✗'} {file}")
    if not exists:
        all_exist = False

print("-" * 20)
print(f"RESULT: {'SUCCESS' if all_exist else 'FAILURE'}")