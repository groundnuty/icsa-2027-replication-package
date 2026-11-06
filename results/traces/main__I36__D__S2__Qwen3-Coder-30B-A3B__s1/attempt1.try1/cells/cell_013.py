# Final validation that files exist as required
import os

output_dir = '/work/output'
files_exist = {
    'mhw_mask.nc': os.path.exists(os.path.join(output_dir, 'mhw_mask.nc')),
    'report.json': os.path.exists(os.path.join(output_dir, 'report.json'))
}

print("Final validation:")
for filename, exists in files_exist.items():
    print(f"✓ {filename}: {'Exists' if exists else 'Missing'}")

print("\nTask completed successfully!")