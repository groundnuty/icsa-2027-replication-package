
import os,subprocess
print(os.getcwd(), os.path.exists('output'))
r=subprocess.run(['python','-c','import os;print(os.getcwd(), os.listdir("output") if os.path.exists("output") else None)'],capture_output=True,text=True);print(r.stdout)
