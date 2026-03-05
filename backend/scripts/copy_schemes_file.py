import shutil
import os

# Define file paths
source_file = 'backend/data/processed/schemes_cleaned.parquet'
target_file = 'backend/data/processed/schemes_with_rules.parquet'

# Check if source file exists
if not os.path.exists(source_file):
    print(f"Error: Source file '{source_file}' not found!")
    exit(1)

# Copy the file
print(f"Copying {source_file} to {target_file}...")
shutil.copy2(source_file, target_file)

# Verify the copy was successful
if os.path.exists(target_file):
    print(f"Successfully created {target_file}")
else:
    print(f"Error: Failed to create {target_file}")
