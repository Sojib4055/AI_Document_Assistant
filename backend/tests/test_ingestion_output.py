from __future__ import annotations

from app.models.document import Chunk


def find_chunk(chunks: list[Chunk], chunk_id: str) -> Chunk:
    return next(chunk for chunk in chunks if chunk.chunk_id == chunk_id)


def test_partex_landscape_pages_are_mapped_to_printed_pages(chunks: list[Chunk]) -> None:
    working_hours = find_chunk(
        chunks,
        "partex-05-a-code-of-conduct-1-working-days-and-hours",
    )
    sick_leave = find_chunk(chunks, "partex-06-b-leave-2-sick-leave")

    assert working_hours.printed_page == 5
    assert working_hours.pdf_page == 4
    assert sick_leave.printed_page == 6
    assert sick_leave.pdf_page == 4


def test_labour_act_front_matter_offset_is_preserved(chunks: list[Chunk]) -> None:
    chapter_two = find_chunk(chunks, "labour-chii-s3-p25")
    chapter_nine = find_chunk(chunks, "labour-chix-s100-p56")

    assert chapter_two.printed_page == 25
    assert chapter_two.pdf_page == 42
    assert chapter_nine.printed_page == 56
    assert chapter_nine.pdf_page == 73


def test_key_numeric_entitlements_survived_extraction(chunks: list[Chunk]) -> None:
    partex_annual = find_chunk(chunks, "partex-06-b-leave-1-annual-leave")
    labour_casual = find_chunk(chunks, "labour-chix-s115-p59")
    labour_festival = find_chunk(chunks, "labour-chix-s118-p60")

    assert "thirty (30) days" in partex_annual.text
    assert "ten days" in labour_casual.text
    assert "eleven days" in labour_festival.text
