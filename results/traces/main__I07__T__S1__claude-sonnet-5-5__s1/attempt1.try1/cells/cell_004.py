print(len(fs.ls(p)))
names=sorted(set(fs.ls(p,detail=False)));print(len(names),names[-1])
import collections
print(collections.Counter(n.split('/')[-1][:8] for n in names).most_common(3))