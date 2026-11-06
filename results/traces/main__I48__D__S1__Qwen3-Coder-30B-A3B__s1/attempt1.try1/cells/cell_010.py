# Verify the final output files exist
import os

print("Final verification:")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")

# Show summary
with open('output/report.json', 'r') as f:
    report = json.load(f)
    
print(f"\nRegion: {report['region']}")
print(f"Baseline period: {report['baseline_analysed']['start']} to {report['baseline_analysed']['end']}")
print(f"Target period: {report['target_analysed']['start']} to {report['target_analysed']['end']}")
print(f"Number of events detected: {len(report['events'])}")
for i, event in enumerate(report['events']):
    print(f"Event {i+1}: {event['onset']} to {event['end']}")