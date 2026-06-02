from chromadb import PersistentClient

client = PersistentClient(path='data/vector_db/chroma')
col = client.get_collection('resumes')
res = col.get(include=['metadatas','documents'])
metas = res.get('metadatas', [])
count = sum(1 for m in metas if isinstance(m, dict) and m.get('source')=='huggingface:ahmedheakl/resume-atlas')
print('resume-atlas-count:', count)
