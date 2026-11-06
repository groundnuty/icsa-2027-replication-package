import os, json
print(os.listdir('output'), [os.path.getsize('output/'+f) for f in os.listdir('output')])
r = json.load(open('output/report.json'))
print(json.dumps({k: (v if k != 'caveats' else v[:60]+'...') for k, v in r.items()}, indent=1))
