
import numpy as np

# Test more carefully
# The Hyndman-Fan type 5 formula: 
# h = (n - 1/2) * p + 1/2
# where h is the 1-indexed position

# For n=4, p=0.5: h = 3.5*0.5 + 0.5 = 2.25
# So the 50th percentile is between position 2 and 3 (1-indexed)
# x = [1,2,3,4]
# position 2 = 2, position 3 = 3
# 2 + 0.25*(3-2) = 2.25

# For n=4, p=0.9: h = 3.5*0.9 + 0.5 = 3.65
# Between position 3 and 4
# 3 + 0.65*(4-3) = 3.65

# But numpy gives 4.0 for hazen at 90th percentile of [1,2,3,4]
# Let me check if numpy might be using a different indexing

# Let me check the numpy source
# Actually, let me just test with a simpler case

x = np.array([1., 2., 3.])
for p in [50, 90]:
    q = np.percentile(x, p, method='hazen')
    print(f"n={len(x)}, p={p}: hazen={q}")

# For n=3, p=0.5: h = 2.5*0.5 + 0.5 = 1.75
# Position 1.75 (1-indexed) -> between x[0]=1 and x[1]=2
# 1 + 0.75*(2-1) = 1.75
# numpy gives...?

# For n=3, p=0.9: h = 2.5*0.9 + 0.5 = 2.25+0.5 = 2.75
# Position 2.75 -> between x[1]=2 and x[2]=3
# 2 + 0.75*(3-2) = 2.75
# numpy gives...?
