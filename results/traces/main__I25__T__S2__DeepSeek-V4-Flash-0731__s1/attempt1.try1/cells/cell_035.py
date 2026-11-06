
import os
import glob

# List files in output directory
print("Files in output directory:")
for f in sorted(os.listdir('output')):
    size = os.path.getsize(os.path.join('output', f))
    print(f"  {f}: {size} bytes")

# Remove intermediate .npy files
for f in glob.glob('output/*.npy'):
    os.remove(f)
    print(f"  Removed {f}")

# Verify the final output files exist
print("\nFinal output files:")
for f in ['mhw_mask.nc', 'report.json']:
    path = os.path.join('output', f)
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  {f}: {size} bytes (OK)")
    else:
        print(f"  {f}: MISSING!")
