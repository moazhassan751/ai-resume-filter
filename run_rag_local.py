import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'ai_resume_filter'))
os.environ.setdefault('SECRET_KEY','test-secret')
os.environ.setdefault('ALLOWED_HOSTS','["localhost","testserver"]')
os.environ.setdefault('EMBEDDING_MOCK_MODE','1')

from app.services.rag_service import RAGService

# Patch retriever via monkeypatch-style assignment
class DummyRetriever:
    async def retrieve(self, query, top_k=10):
        return [
            {'candidate_id':'c1','filename':'a.pdf','category':'eng','skills':'python,sql','score':0.9,'context':'Experienced dev'},
            {'candidate_id':'c2','filename':'b.pdf','category':'eng','skills':'java','score':0.6,'context':'Developer'},
        ]


async def call():
    svc = RAGService.get_instance()
    svc.retriever = DummyRetriever()
    svc._call_gemini = lambda prompt: '{"ranked_candidates": [{"candidate_id":"c1","score":0.9,"reasons":["Match"],"strengths":["X"],"missing_skills":[]}], "summary":"ok","recommended_hires":["c1"], "skill_gaps": []}'
    res = await svc.analyze('Software engineer', top_k=5)
    print(res)

import asyncio
asyncio.run(call())
