from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_resume_filter.services.data_loader import DataPipeline

p = DataPipeline(base_path=ROOT)
loaded = p.load_all_datasets(skip_hf=True)
print('Loaded keys:', list(loaded.keys()))
for k, v in p.get_dataset_stats().items():
    print(f'- {k}: {v}')
