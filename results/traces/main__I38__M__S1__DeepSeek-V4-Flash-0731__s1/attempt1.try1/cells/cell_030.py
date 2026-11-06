
import numpy as np
import json

# Check the report
with open('output/report.json') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# The task specifies the region as lat 60.49-61.69 and lon 17.25-18.45
# My report currently uses the actual grid cell coordinates
# I should use the specified bounds for the region field
