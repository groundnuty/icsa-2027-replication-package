import subprocess
print(subprocess.run(['df','-h','/tmp','/work'],capture_output=True,text=True).stdout)
print(subprocess.run(['mount'],capture_output=True,text=True).stdout[:2000])
