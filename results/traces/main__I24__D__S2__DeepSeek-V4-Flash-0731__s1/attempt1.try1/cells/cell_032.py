
import numpy as np

# Get the full docstring, especially the notes section about methods
doc = np.quantile.__doc__
# Find the notes section
idx = doc.find('Notes')
print(doc[idx:idx+5000])
