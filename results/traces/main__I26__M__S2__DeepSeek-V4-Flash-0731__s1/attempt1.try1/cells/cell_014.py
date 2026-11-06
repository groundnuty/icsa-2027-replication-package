
import numpy as np
import pickle

# Load the setup
with open('/tmp/setup.pkl', 'rb') as f:
    setup = pickle.load(f)

# Check what we have
print("Setup loaded.")

# We need to redo the computation since the variables were in the previous cell
# Let me check if they're still in memory
try:
    print(f"climatology shape: {climatology.shape}")
    print(f"threshold shape: {threshold.shape}")
except NameError:
    print("Variables not in memory. Need to recompute.")

# Actually, let's just redo everything in one comprehensive script
