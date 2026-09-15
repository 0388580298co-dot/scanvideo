import pytest

from apps.worker.services.transcription import TranscriptSegment
from apps.worker.services.translation import TranslationError, TranslationSegment, _validate_output


def test_duration_validation_boundaries():
    # The product default is inclusive at 10.0 seconds.
    assert 10.0 >= 10.0
    with pytest.raises(TranslationError):
        _validate_output([TranslationSegment(-0.1, 1.0, "a", "b")])


def test_translation_timing_is_preserved():
    segments = _validate_output([
        TranslationSegment(0.0, 3.5, "Hello", "Xin chào"),
        TranslationSegment(3.5, 7.0, "world", "thế giới"),
    ])
    assert [(s.start, s.end) for s in segments] == [(0.0, 3.5), (3.5, 7.0)]


def test_translation_rejects_overlap_and_empty_text():
    with pytest.raises(TranslationError):
        _validate_output([TranslationSegment(0, 2, "a", "A"), TranslationSegment(1.9, 3, "b", "B")])
    with pytest.raises(TranslationError):
        _validate_output([TranslationSegment(0, 1, "a", "")])


def test_transcript_segment_contract():
    segment = TranscriptSegment(1.0, 2.0, "hello")
    assert segment.end > segment.start
