from app.services.chunking import fixed_chunks, recursive_chunks

def test_fixed_chunking_overlap():
    chunks=fixed_chunks("a"*2100,size=1000,overlap=100); assert len(chunks)==3; assert chunks[0].text[-100:]==chunks[1].text[:100]

def test_recursive_chunking_preserves_text():
    chunks=recursive_chunks("First paragraph.\n\nSecond paragraph."); assert len(chunks)==1; assert "First paragraph" in chunks[0].text and "Second paragraph" in chunks[0].text
