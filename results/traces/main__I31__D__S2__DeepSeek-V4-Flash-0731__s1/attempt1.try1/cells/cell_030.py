
import os

# Check output files exist
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"{f}: exists ({size} bytes)")
    else:
        print(f"{f}: MISSING!")

# Check the output directory
print("\nOutput directory contents:")
for f in sorted(os.listdir('output')):
    print(f"  {f}")
