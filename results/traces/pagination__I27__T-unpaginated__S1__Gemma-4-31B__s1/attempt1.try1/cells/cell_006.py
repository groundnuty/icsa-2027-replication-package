import json
import pandas as pd

# Correcting the report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

report["baseline_analysed"] = {"start": "1991-12-27", "end": "2003-01-05"}

with open('output/report.json', 'w') as f:
    json.dump(report, f)
