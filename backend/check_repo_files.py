import os

base_dir = 'backend/data/company_problems'
for root, dirs, files in os.walk(base_dir):
    if '.git' in root:
        continue
    non_csv = [f for f in files if not f.endswith('.csv')]
    if non_csv:
        print(f"Non-csv files in {root}:", non_csv)
