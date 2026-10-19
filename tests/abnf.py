"""A small RFC 5234 ABNF compiler: rules cut from a fetched RFC become regular expressions.

It reads what the rules these tests use need: rule names, alternation, concatenation,
repetition (n*m, *, n), groups, options, quoted strings (case-insensitive, as RFC 5234
section 2.3 says) and %x / %d / %b values, ranges and dotted sequences. Prose values
(<...>) are resolved by the caller; recursive rules are refused. Written by hand from
RFC 5234 sections 2 to 4 (https://www.rfc-editor.org/rfc/rfc5234.txt).
"""

from __future__ import annotations

import re

_PAGE_NOISE = re.compile(r"^(RFC \d+ .*\d{4}|.*\[Page \d+\])\s*$")
_RULE_START = re.compile(r"^[ \t]*([A-Za-z][A-Za-z0-9-]*)[ \t]*=(?!/)", re.M)
_TOKEN = re.compile(
    r'\s*(/|\(|\)|\[|\]|\d*\*\d*|\d+|[A-Za-z][A-Za-z0-9-]*|"[^"]*"|<[^>]*>'
    r"|%[xX][0-9A-Fa-f]+(?:(?:\.[0-9A-Fa-f]+)+|-[0-9A-Fa-f]+)?"
    r"|%[dD][0-9]+(?:(?:\.[0-9]+)+|-[0-9]+)?|%[bB][01]+(?:(?:\.[01]+)+|-[01]+)?)"
)
_BASES = {"x": 16, "d": 10, "b": 2}


def clean(text: str) -> str:
    """The RFC text without form feeds, page headers and page footers."""
    lines = text.replace("\f", "").splitlines()
    return "\n".join(line for line in lines if not _PAGE_NOISE.match(line))


def region(text: str, start: str, end: str) -> str:
    """The cleaned text between the last ``start`` heading and the next ``end`` after it."""
    text = clean(text)
    first = text.rindex(start)
    return text[first + len(start) : text.index(end, first)]


def _strip_comment(line: str) -> str:
    quoted = prose = False
    for index, char in enumerate(line):
        if char == '"' and not prose:
            quoted = not quoted
        elif char == "<" and not quoted:
            prose = True
        elif char == ">" and not quoted:
            prose = False
        elif char == ";" and not quoted and not prose:
            return line[:index]
    return line


def rules(text: str) -> dict[str, str]:
    """Rule name (lower case) to its definition, comments removed, for one ABNF region."""
    found: dict[str, str] = {}
    starts = list(_RULE_START.finditer(text))
    for match, following in zip(starts, [*starts[1:], None], strict=True):
        body = text[match.end() : following.start() if following else len(text)]
        lines = [_strip_comment(line) for line in body.splitlines()]
        found[match.group(1).lower()] = " ".join(" ".join(lines).split())
    return found


def _char(code: int) -> str:
    return f"\\U{code:08x}"


class Grammar:
    """Compile named rules to regular expressions; ``prose`` maps <...> texts to regexes."""

    def __init__(self, *rule_sets: dict[str, str], prose: dict[str, str] | None = None) -> None:
        self.rules: dict[str, str] = {}
        for rule_set in rule_sets:
            self.rules.update(rule_set)
        self.prose = prose or {}
        self._done: dict[str, str] = {}
        self._busy: set[str] = set()

    def regex(self, name: str) -> str:
        key = name.lower()
        if key not in self._done:
            if key in self._busy:
                raise ValueError(f"recursive rule {name}")
            self._busy.add(key)
            tokens = _TOKEN.findall(self.rules[key])
            assert "".join(tokens).replace(" ", "") == self.rules[key].replace(" ", ""), key
            pattern, rest = self._alternation(tokens)
            assert not rest, (key, rest)
            self._busy.discard(key)
            self._done[key] = f"(?:{pattern})"
        return self._done[key]

    def compile(self, name: str) -> re.Pattern[str]:
        return re.compile(self.regex(name))

    def _alternation(self, tokens: list[str]) -> tuple[str, list[str]]:
        options = []
        while True:
            pattern, tokens = self._concatenation(tokens)
            options.append(pattern)
            if not tokens or tokens[0] != "/":
                return "|".join(options), tokens
            tokens = tokens[1:]

    def _concatenation(self, tokens: list[str]) -> tuple[str, list[str]]:
        parts = []
        while tokens and tokens[0] not in ("/", ")", "]"):
            part, tokens = self._repetition(tokens)
            parts.append(part)
        assert parts, "empty concatenation"
        return "".join(parts), tokens

    def _repetition(self, tokens: list[str]) -> tuple[str, list[str]]:
        repeat = ""
        if re.fullmatch(r"\d*\*\d*|\d+", tokens[0]):
            repeat, tokens = tokens[0], tokens[1:]
        element, tokens = self._element(tokens)
        if not repeat:
            return element, tokens
        low, star, high = repeat.partition("*")
        if not star:
            return f"(?:{element}){{{int(low)}}}", tokens
        return f"(?:{element}){{{int(low or 0)},{high}}}", tokens

    def _element(self, tokens: list[str]) -> tuple[str, list[str]]:
        head, tokens = tokens[0], tokens[1:]
        if head in ("(", "["):
            inner, tokens = self._alternation(tokens)
            assert tokens and tokens[0] == (")" if head == "(" else "]"), head
            return f"(?:{inner})" + ("?" if head == "[" else ""), tokens[1:]
        if head.startswith('"'):
            return "".join(
                f"[{c.lower()}{c.upper()}]" if c.isalpha() else re.escape(c) for c in head[1:-1]
            ), tokens
        if head.startswith("<"):
            return self.prose[" ".join(head[1:-1].split())], tokens
        if head.startswith("%"):
            base = _BASES[head[1].lower()]
            body = head[2:]
            if "-" in body:
                low, high = (int(part, base) for part in body.split("-"))
                return f"[{_char(low)}-{_char(high)}]", tokens
            return "".join(_char(int(part, base)) for part in body.split(".")), tokens
        return self.regex(head), tokens
