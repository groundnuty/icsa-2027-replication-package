
import numpy as np

# Test numpy's hazen method vs manual calculation
np.random.seed(42)
data = np.random.randn(20)

# numpy hazen
result_np = np.percentile(data, 90, method='hazen')
print(f"numpy hazen 90th percentile: {result_np}")

# Manual hazen (Hyndman-Fan type 5)
# h = (n + 0.5) * p ... no wait
# Actually for type 5 (hazen):
# h = (n - 1/2) * p + 1/2 = (n + 0.5)*p - p/2 + 1/2
# Hmm, let me look this up more carefully.

# Hyndman-Fan type 5: h = (N - 1/2)*p + 1/2
# Wait, that doesn't seem right either.
# Let me check: for type 5, h = (N + 1/4)*p + 3/4? No...

# Let me just check what numpy does
sorted_data = np.sort(data)
n = len(data)
p = 0.9

# Hyndman-Fan type 5: h = (n + 0.5) * p + 0.5
# No, that's type 6.
# Type 5: h = (n - 1/2) * p + 1/2? 
# Actually, for type 5:
# h = (n + 1/2) * p ... 

# Let me just check with known values
x = np.array([1, 2, 3, 4])
q = np.percentile(x, 50, method='hazen')
print(f"Median of [1,2,3,4] with hazen: {q}")

# For n=4, p=0.5:
# h = (4 - 0.5) * 0.5 + 0.5 = 3.5 * 0.5 + 0.5 = 1.75 + 0.5 = 2.25
# Wait that seems wrong. 

# Let me check: for the Hazen method, h = (n - 1/2)*p + 1/2
# For n=4, p=0.5: h = 3.5*0.5 + 0.5 = 2.25
# Interpolating between x[1]=2 and x[2]=3: 2 + 0.25*(3-2) = 2.25

# Hmm, but what does numpy actually do?
# Let me check with the docs or test
print(f"numpy hazen median of [1,2,3,4]: {np.percentile(x, 50, method='hazen')}")

# Let me also check type 5 formula
# According to Hyndman & Fan (1996), type 5 (Hazen):
# h = (n - 1/2)p + 1/2
# For n=4, p=0.5: h = 3.5*0.5 + 0.5 = 2.25
# So the 50th percentile would be x[2] (0-indexed), interpolating:
# Actually, h is 1-indexed. So the value is at position h.
# With h=2.25, the value is between the 2nd and 3rd values (1-indexed).
# x = [1, 2, 3, 4], so the 2nd is 2 and 3rd is 3.
# Result = 2 + 0.25*(3-2) = 2.25

# numpy gives 2.25, so it matches.

print(f"\nCheck 90th percentile for [1,2,3,4] with hazen:")
q90 = np.percentile(x, 90, method='hazen')
print(f"numpy: {q90}")
# n=4, p=0.9: h = 3.5*0.9 + 0.5 = 3.15 + 0.5 = 3.65
# Between 3rd (3) and 4th (4): 3 + 0.65*1 = 3.65
print(f"Expected: 3.65")
