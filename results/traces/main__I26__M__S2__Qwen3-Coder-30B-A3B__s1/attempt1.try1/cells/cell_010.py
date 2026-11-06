import json

# Read and display the complete report
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("Final Report Contents:")
print(json.dumps(report, indent=2))