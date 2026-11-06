
import os, shutil, subprocess
print(subprocess.run(['python','-c','import os;print(os.getcwd());os.makedirs("output",exist_ok=True);print(os.path.exists("/tmp/w/output/report.json"))'],capture_output=True,text=True).stdout)
