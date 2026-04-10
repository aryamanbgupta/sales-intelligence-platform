"""Tests for research._extract_citations — pure function with mock response objects."""

from app.pipeline.research import _extract_citations


class _FakeResponse:
    """Minimal mock of an OpenAI chat completion response."""

    def __init__(self, citations=None, model_extra=None, dump=None):
        self._citations = citations
        self._model_extra = model_extra
        self._dump = dump

        # Only set the attribute if explicitly provided
        if citations is not None:
            self.citations = citations

    def __getattr__(self, name):
        if name == "citations":
            raise AttributeError
        if name == "model_extra":
            return self._model_extra
        raise AttributeError(name)

    def model_dump(self):
        return self._dump or {}


class TestExtractFromCitationsAttr:

    def test_extracts_from_citations_attr(self):
        resp = type("Resp", (), {"citations": ["https://bbb.org/abc", "https://yelp.com/abc"]})()
        result = _extract_citations(resp)
        assert result == ["https://bbb.org/abc", "https://yelp.com/abc"]


class TestExtractFallbacks:

    def test_extract_from_model_extra(self):
        resp = _FakeResponse(
            model_extra={"citations": ["https://example.com"]},
        )
        result = _extract_citations(resp)
        assert result == ["https://example.com"]

    def test_extract_from_model_dump(self):
        resp = _FakeResponse(
            model_extra=None,
            dump={"citations": ["https://example.com/dump"]},
        )
        result = _extract_citations(resp)
        assert result == ["https://example.com/dump"]

    def test_empty_citations(self):
        resp = _FakeResponse(model_extra=None, dump={})
        result = _extract_citations(resp)
        assert result == []


class TestCitationFiltering:

    def test_filters_none_values(self):
        resp = type("Resp", (), {"citations": ["https://valid.com", None, "https://also-valid.com"]})()
        result = _extract_citations(resp)
        assert result == ["https://valid.com", "https://also-valid.com"]

    def test_converts_to_strings(self):
        resp = type("Resp", (), {"citations": [123, "https://example.com"]})()
        result = _extract_citations(resp)
        assert all(isinstance(c, str) for c in result)
        assert result == ["123", "https://example.com"]
