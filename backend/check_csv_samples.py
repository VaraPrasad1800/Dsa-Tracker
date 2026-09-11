import os
import csv

base_dir = 'data/company_problems' if os.path.exists('data/company_problems') else 'backend/data/company_problems'
found = 0

for root, dirs, files in os.walk(base_dir):
    if '.git' in root:
        continue
    for f in files:
        if f.endswith('.csv'):
            fpath = os.path.join(root, f)
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                reader = csv.DictReader(fp)
                for row in reader:
                    link = row.get('Link', '').strip()
                    title = row.get('Title', '').strip()
                    diff = row.get('Difficulty', '').strip()
                    freq = row.get('Frequency', '').strip()
                    topics = row.get('Topics', '').strip()
                    if link and title:
                        print(f"File: {fpath} | Title: {title} | Diff: {diff} | Link: {link} | Freq: {freq}")
                        found += 1
                        if found >= 20:
                            exit(0)
