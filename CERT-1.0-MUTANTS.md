# contentdisp 1.0.0 author mutation table

The author mutation round of [CERT-1.0-REPORT.md](https://github.com/JaviLianes8/contentdisp/blob/main/CERT-1.0-REPORT.md).
Each mutant was applied alone to a fresh clone of `release/1.0.0` at 8e49dcb on another
machine (CPython 3.14), with the fetched sources, Node.js and the two jshttp parsers,
werkzeug 3.1.9, aiohttp 3.14.5, multipart 2.0.1 and the 0.2.1 oracle present, and the full
suite run with `-x` and a 300 s per-test limit. The first failing test is listed. The
unmutated suite passed after the round.

| Mutant | Module | Change | Killed by |
| --- | --- | --- | --- |
| M01 | `_grammar.py` | tchar drops the backtick | `test_oracles_node.py::test_strict_mode_agrees_with_release_1_on_the_shared_grammar` |
| M02 | `_grammar.py` | qdtext upper bound off by one (DEL allowed) | `test_positions.py::test_strict_errors_point_at_the_first_offending_character` |
| M03 | `_grammar.py` | quoted-pair drops the escaped character | `test_browser_corpus.py::test_the_offered_file_name_matches_the_corpus` |
| M04 | `_grammar.py` | unterminated quoted-string position off by one | `test_positions.py::test_strict_errors_point_at_the_first_offending_character` |
| M05 | `_ext_value.py` | ISO-8859-1 octets 0x80 to 0x9F accepted | `test_browser_corpus.py::test_strict_mode_rejects_exactly_what_the_corpus_marks_invalid` |
| M06 | `_ext_value.py` | encoder leaves `%` unescaped | `test_build.py::test_characters_appendix_d_avoids_move_to_the_extended_form` |
| M07 | `_langtag.py` | numeric region of two digits instead of three | `test_spec_grammar.py::test_language_tags_are_exactly_the_rfc_5646_rule` |
| M08 | `_parse.py` | strict mode accepts repeated parameters | `test_browser_corpus.py::test_strict_mode_rejects_exactly_what_the_corpus_marks_invalid` |
| M09 | `_parse.py` | plain `filename` overrides `filename*` | doctest `contentdisp.ContentDisposition.filename` |
| M10 | `_parse.py` | lenient mode keeps the last repeated parameter | doctest `contentdisp._parse.parse` |
| M11 | `_parse.py` | lenient mode keeps NUL | `test_fuzz.py::test_lenient_parsing_never_fails_and_returns_clean_text` |
| M12 | `_parse.py` | segment splitter ignores backslash escapes | `test_browser_corpus.py::test_the_offered_file_name_matches_the_corpus` |
| M13 | `_parse.py` | ext-value error points after the value, not its start | `test_docs.py::test_every_guide_example_runs_and_prints_its_comment` |
| M14 | `_build.py` | form-data leaves a backslash raw | `test_build.py::test_form_data_escapes_only_cr_lf_quote_and_backslash` |
| M15 | `_build.py` | ASCII fallback keeps `%HH` sequences | `test_build.py::test_characters_appendix_d_avoids_move_to_the_extended_form` |
| M16 | `_build.py` | duplicate names compared with case | `test_build.py::test_extra_parameters_use_hyphens_and_lower_case` |
| M17 | `_safe.py` | device name `CONIN$` dropped | `test_safe_filename.py::test_windows_device_names_are_prefixed` |
| M18 | `_safe.py` | truncation budget off by one | `test_docs.py::test_every_guide_example_runs_and_prints_its_comment` |
| M19 | `_safe.py` | extension taken after the first dot | `test_docs.py::test_every_guide_example_runs_and_prints_its_comment` |
| M20 | `_safe.py` | joiners removed like other format characters | `test_safe_filename.py::test_format_characters_are_removed_but_joiners_inside_a_name_stay` |
| M21 | `_model.py` | `is_attachment` compares `inline` with the wrong case | doctest `contentdisp.ContentDisposition` |
| M22 | `_errors.py` | message cut keeps 40 characters plus `...` (43) | survived at 8e49dcb; killed at b81458e by `test_hostile.py::test_huge_input_never_reaches_a_message_whole` |
| M23 | `_ext_value.py` | strict mode skips the language tag check | `test_oracle.py::test_strict_mode_accepts_exactly_what_the_oracle_accepts` |
| M24 | `_model.py` | `params` values not type checked | `test_contract_api.py::test_wrong_argument_types_raise_type_error` |

M22 showed that no test pinned the exact length of the quoted input in a message (the
old check only refused 41 repeated characters). The contract added in b81458e asserts
the cut is exactly 40 characters (opening quote, 36 characters, `...`); M22 applied to
that commit fails it.
