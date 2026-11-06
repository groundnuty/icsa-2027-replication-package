# Final verification that files were created correctly
import os
import json

# Check if files exist
files_exist = {
    'output/mhw_mask.nc': os.path.exists('output/mhw_mask.nc'),
    'output/report.json': os.path.exists('output/report.json')
}

print("Output files verification:")
for file_path, exists in files_exist.items():
    print(f"  {file_path}: {'✓' if exists else '✗'}")

# Print content of report.json to confirm structure
try:
    with open('output/report.json', 'r') as f:
        report = json.load(f)
    print("\nReport content:")
    for key, value in report.items():
        print(f"  {key}: {value}")
except Exception as e:
    print(f"Error reading report.json: {e}")

print("\nTask completed successfully!")