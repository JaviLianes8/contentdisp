import contentdisp


def test_build_ascii_filename_emits_no_extended_form() -> None:
    header = contentdisp.build("attachment", "report.pdf")
    assert header == 'attachment; filename="report.pdf"'
    assert "filename*" not in header


def test_build_without_filename() -> None:
    assert contentdisp.build("inline") == "inline"


def test_build_non_ascii_filename_emits_both_forms() -> None:
    header = contentdisp.build("attachment", "€ rates.txt")
    assert header == "attachment; filename=\"_ rates.txt\"; filename*=UTF-8''%E2%82%AC%20rates.txt"


def test_build_escapes_quotes_in_ascii_filename() -> None:
    header = contentdisp.build("attachment", 'a"b.txt')
    assert header == 'attachment; filename="a\\"b.txt"'


def test_build_extra_parameters_use_hyphens() -> None:
    header = contentdisp.build("form-data", "a.txt", name="file")
    assert header == 'form-data; filename="a.txt"; name="file"'


def test_build_round_trips_through_parse() -> None:
    name = "éè résumé.pdf"
    parsed = contentdisp.parse(contentdisp.build("attachment", name))
    assert parsed.type == "attachment"
    assert parsed.filename == name
