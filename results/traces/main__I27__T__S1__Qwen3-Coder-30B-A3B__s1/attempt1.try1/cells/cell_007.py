# Verify that the output files were created
import os
print("Output files created:")
print("-" * 30)
if os.path.exists('output/report.json'):
    print("✓ output/report.json")
else:
    print("✗ output/report.json")

if os.path.exists('output/mhw_mask.nc'):
    print("✓ output/mhw_mask.nc")
else:
    print("✗ output/mhw_mask.nc")

# Show content of report.json
if os.path.exists('output/report.json'):
    with open('output/report.json', 'r') as f:
        import json
        report = json.load(f)
        print("\nReport content:")
        print(json.dumps(report, indent=2))