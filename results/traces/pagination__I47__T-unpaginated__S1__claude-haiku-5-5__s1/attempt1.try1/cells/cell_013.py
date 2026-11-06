import subprocess, os
print(os.getcwd())
r=subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True)
print(r.stdout, r.stderr[-1000:])
print(os.path.exists('output/mhw_mask.nc'), os.path.exists('output/report.json'))
print(open('output/report.json').read()[:400])
