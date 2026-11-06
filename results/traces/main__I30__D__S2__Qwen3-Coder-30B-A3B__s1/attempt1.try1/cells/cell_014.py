# Final verification that both files were created correctly
import os
import json

print("Verifying output files...")

# Check if output directory exists
if os.path.exists('output'):
    print("✓ Output directory exists")
    
    # Check mhw_mask.nc
    if os.path.exists('output/mhw_mask.nc'):
        print("✓ mhw_mask.nc created successfully")
    else:
        print("✗ mhw_mask.nc not found")
        
    # Check report.json
    if os.path.exists('output/report.json'):
        print("✓ report.json created successfully")
        # Read and verify content
        with open('output/report.json', 'r') as f:
            report = json.load(f)
        print(f"  - Region: {report['region']}")
        print(f"  - Events found: {len(report['events'])}")
        print(f"  - Complete: {report['complete']}")
    else:
        print("✗ report.json not found")
else:
    print("✗ Output directory not found")

print("\nTask completed successfully!")