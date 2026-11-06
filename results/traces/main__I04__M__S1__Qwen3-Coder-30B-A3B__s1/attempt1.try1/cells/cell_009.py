# Verify that the files were created
import os
print("Files created:")
if os.path.exists("output/mhw_mask.nc"):
    print("- output/mhw_mask.nc: Created successfully")
else:
    print("- output/mhw_mask.nc: Not found")

if os.path.exists("output/report.json"):
    print("- output/report.json: Created successfully")
else:
    print("- output/report.json: Not found")

# Print summary of the report
if os.path.exists("output/report.json"):
    with open("output/report.json", "r") as f:
        import json
        report = json.load(f)
        print("\nReport Summary:")
        print(f"Region: {report['region']}")
        print(f"Baseline period: {report['baseline_analysed']}")
        print(f"Target period: {report['target_analysed']}")
        print(f"Number of events found: {len(report['events'])}")
        if report['events']:
            for i, event in enumerate(report['events']):
                print(f"  Event {i+1}: {event['onset']} to {event['end']}")