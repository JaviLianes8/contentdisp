# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- Parse a Content-Disposition header into type, filename and parameters, preferring
  the decoded RFC 5987 `filename*` over the plain fallback.
- Build a header from its parts, emitting an ASCII fallback plus a correct `filename*`
  for non-ASCII names.
- Tolerate malformed parameters, bad extended values and unknown charsets on parse.
