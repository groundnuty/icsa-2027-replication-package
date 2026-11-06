
import subprocess
print(subprocess.run(['python','/work/mhw/run_batch.py','900'],capture_output=True,text=True).stdout)
