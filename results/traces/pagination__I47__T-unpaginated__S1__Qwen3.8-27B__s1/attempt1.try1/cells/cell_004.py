
import subprocess
print(subprocess.run(['pip', 'list'], capture_output=True, text=True).stdout[:3000])
