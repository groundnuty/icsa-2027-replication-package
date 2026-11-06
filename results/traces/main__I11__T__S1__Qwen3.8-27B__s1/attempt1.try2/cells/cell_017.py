
lines = open("/work/compute.py").readlines()
for n in range(66, 82):
    print(n+1, lines[n].rstrip())
