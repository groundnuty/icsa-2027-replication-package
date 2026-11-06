import os,shutil
print(os.getcwd())
os.makedirs('output',exist_ok=True)
for f in ['mhw_mask.nc','report.json']: shutil.copy('/tmp/w/output/'+f,'output/'+f)
print(os.path.abspath('output'), os.listdir('output'))