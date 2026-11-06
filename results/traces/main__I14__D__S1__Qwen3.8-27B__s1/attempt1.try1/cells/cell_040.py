import os, subprocess
out = subprocess.run(['bash','-lc','ps aux | head -30; echo ---; free -h'], capture_output=True, text=True)
print(out.stdout[-3000:])
print(out.stderr[-500:])