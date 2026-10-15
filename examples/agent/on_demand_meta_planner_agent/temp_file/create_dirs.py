import os
import json

# Create directory structure programmatically
directories = ['notebooks', 'data', 'results', 'configs']

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    # Create a placeholder file to ensure directory is tracked
    with open(os.path.join(directory, '.gitkeep'), 'w') as f:
        f.write('# Keep this directory in git\n')

print("Directory structure created successfully!")
print("Directories:", directories)