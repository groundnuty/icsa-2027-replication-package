
import os
print("output/mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("output/report.json exists:", os.path.exists('output/report.json'))
print("mhw_mask.nc size:", os.path.getsize('output/mhw_mask.nc'), "bytes")
print("report.json size:", os.path.getsize('output/report.json'), "bytes")

# Verify report content
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport keys:", list(report.keys()))
print("Events:", report['events'])
print("Complete:", report['complete'])
print("Region:", report['region'])
print("Baseline:", report['baseline_analysed'])
print("Target:", report['target_analysed'])
