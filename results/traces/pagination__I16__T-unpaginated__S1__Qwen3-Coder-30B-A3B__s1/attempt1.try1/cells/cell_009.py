# Verify the files were created correctly
import os
import json

if os.path.exists("output/report.json") and os.path.exists("output/mhw_mask.nc"):
    print("✅ Both output files created successfully")
    
    # Read and display the report content
    with open("output/report.json", "r") as f:
        report = json.load(f)
        print(f"Region: {report['region']}")
        print(f"Baseline period: {report['baseline_analysed']}")
        print(f"Target period: {report['target_analysed']}")
        print(f"Events found: {len(report['events'])}")
        if report['events']:
            print(f"First event: {report['events'][0]}")
else:
    print("❌ Output files not found")