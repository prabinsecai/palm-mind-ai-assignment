from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import ingestion_service, rag_service
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGService

class FakeIngestion:
    async def ingest(self,filename,content_type,data,strategy):
        class D: pass
        d=D(); d.id=uuid4(); d.filename=filename; d.chunk_count=2; return d
class FakeRAG:
    async def chat(self,session_id,message):
        return "Test RAG answer",[],None,None

app.dependency_overrides[ingestion_service]=lambda: FakeIngestion()
app.dependency_overrides[rag_service]=lambda: FakeRAG()
client=TestClient(app)

def test_health():
    r=client.get("/health"); assert r.status_code==200; assert r.json()=={"status":"ok"}

def test_document_ingestion_api():
    r=client.post("/api/v1/documents/ingest",files={"file":("resume.txt",b"Palm Mind hiring role", "text/plain")},data={"chunking_strategy":"fixed"})
    assert r.status_code==201; body=r.json(); assert body["filename"]=="resume.txt"; assert body["chunks_created"]==2

def test_chat_api():
    r=client.post("/api/v1/chat",json={"session_id":"demo","message":"What is the role?"})
    assert r.status_code==200; assert r.json()["answer"]=="Test RAG answer"

def test_openapi_exposes_two_required_apis():
    paths=client.get("/openapi.json").json()["paths"]
    assert "/api/v1/documents/ingest" in paths
    assert "/api/v1/chat" in paths
