import asyncio
import os
from pathlib import Path

# ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_resume_filter.services.data_service import get_data_service, init_data_service

os.environ['SKIP_HF_DATASET'] = '1'

async def main():
    await init_data_service()
    svc = get_data_service()
    print('Loaded datasets:', svc.list_datasets())
    stats = svc.get_dataset_stats()
    for k, v in stats.items():
        print(f"- {k}: {v}")

if __name__ == '__main__':
    asyncio.run(main())
