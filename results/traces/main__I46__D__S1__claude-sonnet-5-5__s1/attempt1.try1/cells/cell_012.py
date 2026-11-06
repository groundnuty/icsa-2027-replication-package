import os,glob
sz=[(os.path.getsize(f),f) for f in glob.glob('/work/c/*.nc')]
bad=[f for s,f in sz if s<3000];print(len(bad),sorted(set(s for s,f in sz))[:5])
for f in bad: os.remove(f)
for f in glob.glob('/work/t_*'):os.remove(f)