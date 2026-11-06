
import os
import json

# Check output files
print("Output directory contents:", os.listdir('output'))
print()

# Check if mhw_mask.npy exists in /tmp
print("/tmp files:", os.listdir('/tmp'))
print()

# Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("Report contents:")
print(json.dumps(report, indent=2))
