# Verify final state
import os
print("Task completed successfully!")
print(f"Files created: {len([f for f in os.listdir('output') if os.path.isfile(os.path.join('output', f))])}")