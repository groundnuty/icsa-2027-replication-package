# Final verification that output files were created
import os
import json

# Check if output files exist
if os.path.exists('output/mhw_mask.nc') and os.path.exists('output/report.json'):
    print("✓ Both output files created successfully")
    
    # Read and display the report content
    with open('output/report.json', 'r') as f:
        report = json.load(f)
        print("Report content:")
        print(json.dumps(report, indent=2))
else:
    print("❌ Output files not found")