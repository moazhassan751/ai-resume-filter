from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_resume_filter.services.data_service import get_data_service

svc = get_data_service()
loader = svc._loader
print('Using loader base_path=', loader.base_path)
try:
    df = loader.load_csv('resume_data.csv')
    print('resume_data_csv rows=', len(df))
except Exception as e:
    print('resume_data_csv error:', e)

try:
    df2 = loader.load_csv('Resume/Resume.csv')
    print('resume_csv rows=', len(df2))
except Exception as e:
    print('resume_csv error:', e)

try:
    js = loader.load_jsonl('resumes_dataset.jsonl')
    print('resumes_jsonl records=', len(js))
except Exception as e:
    print('resumes_jsonl error:', e)

try:
    pdfs = loader.load_pdf_directory('data/data')
    print('pdf categories=', len(pdfs))
except Exception as e:
    print('pdfs error:', e)
