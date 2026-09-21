from app.infrastructure.openai_client import OpenAIService
from app.infrastructure.qdrant_store import QdrantStore
from app.infrastructure.redis_memory import ChatMemory
from app.repositories.booking_repository import BookingRepository
from app.schemas.chat import BookingDetails

class RAGService:
    def __init__(self,llm:OpenAIService,qdrant:QdrantStore,memory:ChatMemory,bookings:BookingRepository): self.llm=llm; self.qdrant=qdrant; self.memory=memory; self.bookings=bookings
    async def chat(self,session_id:str,message:str):
        history=await self.memory.get(session_id)
        booking_data=await self.llm.extract_booking(message,history)
        booking=None; booking_id=None
        if booking_data and booking_data.get("intent"):
            required=(booking_data.get("name"),booking_data.get("email"),booking_data.get("date"),booking_data.get("time"))
            if all(required):
                details=BookingDetails(name=booking_data["name"],email=booking_data["email"],date=booking_data["date"],time=booking_data["time"])
                saved=await self.bookings.create(details.name,str(details.email),details.date,details.time)
                booking=details; booking_id=saved.id
                answer=f"Thanks, {details.name}. Your interview is booked for {details.date} at {details.time}. A confirmation can be sent to {details.email}."
                await self.memory.append(session_id,{"role":"user","content":message},{"role":"assistant","content":answer})
                return answer,[],booking,booking_id
            answer="I can book the interview. Please provide your full name, email address, preferred date (YYYY-MM-DD), and time (HH:MM)."
            await self.memory.append(session_id,{"role":"user","content":message},{"role":"assistant","content":answer})
            return answer,[],None,None
        vector=(await self.llm.embed([message]))[0]
        hits=await self.qdrant.search(vector,limit=5)
        context="\n\n".join(f"[{h['filename']}#{h['chunk_index']}]\n{h['text']}" for h in hits)
        answer=await self.llm.answer(message,context,history)
        await self.memory.append(session_id,{"role":"user","content":message},{"role":"assistant","content":answer})
        sources=[{"document_id":h["document_id"],"filename":h["filename"],"chunk_index":h["chunk_index"],"score":h["score"]} for h in hits]
        return answer,sources,None,None
