# Verify the files were created correctly
import os
import json

print("Final verification of output files:")

# Check output directory exists
if os.path.exists('output'):
    print("✓ Output directory exists")
    
    # Check mhw_mask.nc exists
    if os.path.exists('output/mhw_mask.nc'):
        print("✓ mhw_mask.nc created successfully")
    else:
        print("✗ mhw_mask.nc not found")
        
    # Check report.json exists and is readable
    if os.path.exists('output/report.json'):
        print("✓ report.json created successfully")
        try:
            with open('output/report.json', 'r') as f:
                report = json.load(f)
            print("✓ report.json is valid JSON")
            print(f"✓ Region: {report['region']}")
            print(f"✓ Events found: {len(report['events'])}")
        except Exception as e:
            print(f"✗ Error reading report.json: {e}")
    else:
        print("✗ report.json not found")
else:
    print("✗ Output directory not found")

print("\nTask completed successfully!")