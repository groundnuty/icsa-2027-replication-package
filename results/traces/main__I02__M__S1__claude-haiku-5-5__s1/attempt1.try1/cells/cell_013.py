import os,shutil,subprocess
print(os.getcwd())
os.makedirs('output',exist_ok=True)
shutil.copy('/tmp/output/mhw_mask.nc','output/mhw_mask.nc'); shutil.copy('/tmp/output/report.json','output/report.json')
print(os.path.abspath('output'), os.listdir('output'))