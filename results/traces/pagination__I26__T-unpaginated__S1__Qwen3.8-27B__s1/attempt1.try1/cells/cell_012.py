import subprocess
r = subprocess.run(['python', '/work/mhw_analyse.py'], capture_output=True, text=True, timeout=3600)
print(r.stdout[-4000:])
print("STDERR:", r.stderr[-1500:])
