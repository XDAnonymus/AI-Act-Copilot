from app.text_processing import chunk_text, normalize_text, split_sections


def test_normalize_text_joins_hyphenated_line_breaks():
    assert "classification" in normalize_text("classifi-\ncation")


def test_split_sections_tracks_article():
    sections, current = split_sections("Article 6\nClassification rules\nText")
    assert current == "Article 6"
    assert sections[0][0] == "Article 6"


def test_chunk_text_respects_size():
    text = "\n\n".join(["A" * 500 for _ in range(8)])
    chunks = chunk_text(text, max_chars=1200, overlap_chars=100)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 1400 for chunk in chunks)
