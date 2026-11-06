# Clean up any temporary files if needed
import os
import shutil

# Verify final state
print("Final status check:")
print("- mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("- report.json exists:", os.path.exists('output/report.json'))

# Print a summary of the events found
with open('output/report.json', 'r') as f:
    import json
    report = json.load(f)
    print(f"\nSuccessfully identified {len(report['events'])} regional MHW events:")
    for i, event in enumerate(report['events'], 1):
        print(f"  {i}. {event['onset']} to {event['end']}")