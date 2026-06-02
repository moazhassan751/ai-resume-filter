from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
print('PROJECT_ROOT=', ROOT)
files = [
    'resume_data.csv',
    'Resume/Resume.csv',
    'resumes_dataset.jsonl',
    'CareerCorpus  A Comprehensive Dataset of Annotated/CareerCorpus.xlsx',
    'data/data'
]
for f in files:
    p = ROOT / f
    print(f, '->', p.exists(), p)
