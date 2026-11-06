import subprocess
print(subprocess.run("ls -R /data/icsa2027_data_20261101T090944Z/s1z | head -100; du -sh /data/icsa2027_data_20261101T090944Z/s1z",shell=True,capture_output=True,text=True).stdout)