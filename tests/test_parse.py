import contentdisp


def test_plain_attachment_with_filename() -> None:
    result = contentdisp.parse('attachment; filename="report.pdf"')
    assert result.type == "attachment"
    assert result.filename == "report.pdf"
    assert result.params == {"filename": "report.pdf"}


def test_inline_without_parameters() -> None:
    result = contentdisp.parse("inline")
    assert result.type == "inline"
    assert result.filename is None
    assert result.params == {}


def test_extended_filename_is_utf8_decoded() -> None:
    result = contentdisp.parse("attachment; filename*=UTF-8''%E2%82%AC%20rates.txt")
    assert result.filename == "€ rates.txt"


def test_extended_filename_wins_over_plain() -> None:
    header = "attachment; filename=\"EURO rates.txt\"; filename*=UTF-8''%E2%82%AC%20rates.txt"
    result = contentdisp.parse(header)
    assert result.filename == "€ rates.txt"


def test_extended_value_honours_declared_charset() -> None:
    result = contentdisp.parse("attachment; filename*=ISO-8859-1''%A3%20price.txt")
    assert result.filename == "\xa3 price.txt"


def test_semicolon_inside_quoted_value_is_not_a_separator() -> None:
    result = contentdisp.parse('attachment; filename="a;b.txt"')
    assert result.filename == "a;b.txt"


def test_escaped_quote_inside_value() -> None:
    result = contentdisp.parse('attachment; filename="a\\"b.txt"')
    assert result.filename == 'a"b.txt'


def test_additional_parameters_are_kept() -> None:
    result = contentdisp.parse('form-data; name="file"; filename="a.txt"')
    assert result.params["name"] == "file"
    assert result.params["filename"] == "a.txt"


def test_type_is_lowercased() -> None:
    assert contentdisp.parse("Attachment").type == "attachment"


def test_malformed_parameter_without_equals_is_ignored() -> None:
    result = contentdisp.parse('attachment; broken; filename="a.txt"')
    assert result.filename == "a.txt"


def test_malformed_extended_value_falls_back_to_raw() -> None:
    result = contentdisp.parse("attachment; filename*=not-an-ext-value")
    assert result.filename == "not-an-ext-value"


def test_unknown_charset_falls_back_to_raw() -> None:
    raw = "bogus-charset''%41"
    result = contentdisp.parse(f"attachment; filename*={raw}")
    assert result.filename == raw
