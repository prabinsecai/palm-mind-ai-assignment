from app.services.chunking import fixed_chunks, recursive_chunks


def test_fixed_chunking_overlap():
    chunks = fixed_chunks("a" * 2100, size=1000, overlap=100)
    assert len(chunks) == 3
    assert chunks[0].text[-100:] == chunks[1].text[:100]


def test_recursive_chunking_preserves_text():
    chunks = recursive_chunks("First paragraph.\n\nSecond paragraph.")
    assert len(chunks) == 1
    assert "First paragraph" in chunks[0].text
    assert "Second paragraph" in chunks[0].text


def test_recursive_chunks_preserve_all_text_with_paragraph_overlap() -> None:
    text = "A" * 900 + "\n\n" + "B" * 900 + " END_OF_P2"
    size = 1000
    overlap = 150
    chunks = recursive_chunks(text, size=size, overlap=overlap)

    assert chunks
    assert all(len(chunk.text) <= size for chunk in chunks)
    assert "END_OF_P2" in "".join(chunk.text for chunk in chunks)

    covered = [False] * len(text)
    start = 0
    for chunk in chunks:
        assert text[start : start + len(chunk.text)] == chunk.text
        for index in range(start, start + len(chunk.text)):
            covered[index] = True
        start += len(chunk.text) - overlap
    assert all(covered)


def test_recursive_chunks_cover_long_single_paragraph() -> None:
    text = "0123456789" * 240
    chunks = recursive_chunks(text, size=250, overlap=40)

    assert all(len(chunk.text) <= 250 for chunk in chunks)
    assert (
        "".join(chunk.text if index == 0 else chunk.text[40:] for index, chunk in enumerate(chunks))
        == text
    )


def test_fixed_chunking_rejects_invalid_overlap() -> None:
    import pytest

    with pytest.raises(ValueError):
        fixed_chunks("content", size=10, overlap=10)

    with pytest.raises(ValueError):
        fixed_chunks("content", size=10, overlap=-1)
