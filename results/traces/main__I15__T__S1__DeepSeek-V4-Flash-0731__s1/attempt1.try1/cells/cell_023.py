import numpy as np
print("numpy version:", np.__version__)

# Test various scenarios
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
for p in [0.1, 0.5, 0.9]:
    result = np.percentile(data, p*100, method='hazen')
    print(f"p={p}: numpy hazen = {result}")

# Check the formula
# For data [1..10]:
# If h = (N+1)p = 11p
# p=0.1: h=1.1, value between x[1]=1 and x[2]=2 at 10%: 1.1
# p=0.5: h=5.5, value between x[5]=5 and x[6]=6 at 50%: 5.5
# p=0.9: h=9.9, value between x[9]=9 and x[10]=10 at 90%: 9.9

print("\nExpected if h=(N+1)p:")
print("p=0.1: 1.1")
print("p=0.5: 5.5")
print("p=0.9: 9.9")

print("\nExpected if h=Np+0.5:")
print("p=0.1: 1.5")
print("p=0.5: 5.5")
print("p=0.9: 9.5")
