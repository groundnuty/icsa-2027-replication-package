import subprocess
r = subprocess.run(['python', '/work/mhw_load.py'], capture_output=True, text=True, timeout=4500)
print(r.stdout[-3000:])
print("STDERR:", r.stderr[-2000:])
