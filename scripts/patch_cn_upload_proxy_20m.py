"""Prepare a narrow upload boundary overlay from a pinned, actual Nginx config.

This tool never contacts Docker or a server and never overwrites its input.
Only the three material proxy routes gain a 21 MiB request envelope; the
application continues to enforce a 20 MiB file payload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


UPLOAD_PATTERN = r"^/api/v1/(?:resume|job-descriptions|knowledge/collections/[^/]+)/uploads/proxy$"
UPLOAD_LOCATION = f"location ~ {UPLOAD_PATTERN}"
PATCH_MARKER = "# CN material upload envelope 20261021; file payload remains 20 MiB."
SAMPLE_PATHS = (
    "/api/v1/resume/uploads/proxy",
    "/api/v1/job-descriptions/uploads/proxy",
    "/api/v1/knowledge/collections/synthetic-collection/uploads/proxy",
)


class PatchRefused(ValueError):
    """A fixed refusal code; never includes the private configuration."""


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Directive:
    words: tuple[str, ...]
    start: int
    end: int
    body_start: int | None = None
    body_end: int | None = None
    children: tuple["Directive", ...] = ()


@dataclass(frozen=True)
class PatchResult:
    content: bytes
    original_sha256: str
    candidate_sha256: str
    inserted_bytes: int


def _tokens(config: str) -> list[Token]:
    result: list[Token] = []
    i = 0
    while i < len(config):
        if config[i].isspace():
            i += 1
            continue
        if config[i] == "#":
            newline = config.find("\n", i)
            i = len(config) if newline < 0 else newline + 1
            continue
        start = i
        if config[i] in "{};":
            i += 1
            result.append(Token(config[start:i], start, i))
            continue
        chars: list[str] = []
        quote: str | None = None
        while i < len(config):
            char = config[i]
            if char == "\\" and i + 1 < len(config):
                # Keep regex escapes; the parser only interprets structure.
                chars.extend((char, config[i + 1]))
                i += 2
                continue
            if quote:
                if char == quote:
                    quote = None
                else:
                    chars.append(char)
                i += 1
                continue
            if char in "\"'":
                quote = char
                i += 1
                continue
            if char.isspace() or char in "{};#":
                break
            chars.append(char)
            i += 1
        if quote or i == start:
            raise PatchRefused("unsupported_config_syntax")
        result.append(Token("".join(chars), start, i))
    return result


def _parse(config: str) -> tuple[Directive, ...]:
    tokens = _tokens(config)

    def walk(index: int, nested: bool) -> tuple[tuple[Directive, ...], int]:
        nodes: list[Directive] = []
        while index < len(tokens):
            if tokens[index].text == "}":
                if not nested:
                    raise PatchRefused("unbalanced_config")
                return tuple(nodes), index
            start = index
            while index < len(tokens) and tokens[index].text not in {"{", "}", ";"}:
                index += 1
            if index == start or index >= len(tokens) or tokens[index].text == "}":
                raise PatchRefused("unsupported_config_syntax")
            words = tuple(token.text for token in tokens[start:index])
            if tokens[index].text == ";":
                nodes.append(Directive(words, tokens[start].start, tokens[index].end))
                index += 1
            else:
                opening = tokens[index]
                children, closing_index = walk(index + 1, True)
                closing = tokens[closing_index]
                nodes.append(Directive(words, tokens[start].start, closing.end, opening.end, closing.start, children))
                index = closing_index + 1
        if nested:
            raise PatchRefused("unbalanced_config")
        return tuple(nodes), index

    return walk(0, False)[0]


def _directive_line_span(config: str, node: Directive) -> tuple[int, int]:
    start = config.rfind("\n", 0, node.start) + 1
    if config[start:node.start].strip():
        start = node.start
    end = node.end
    rest = config[end:config.find("\n", end) if "\n" in config[end:] else len(config)]
    if not rest.strip():
        end += len(rest)
        if end < len(config) and config[end] == "\n":
            end += 1
    return start, end


def patch_config(original: bytes, *, expected_sha256: str) -> PatchResult:
    digest = hashlib.sha256(original).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or digest != expected_sha256:
        raise PatchRefused("baseline_sha_mismatch")
    try:
        config = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchRefused("config_not_utf8") from exc
    if "\r" in config or PATCH_MARKER in config:
        raise PatchRefused("unsupported_or_already_patched_config")
    roots = _parse(config)
    servers = [node for node in roots if node.words == ("server",)]
    if len(servers) != 1:
        raise PatchRefused("expected_single_server")
    locations = [node for node in servers[0].children if node.words[0] == "location"]
    generics = [node for node in locations if node.words == ("location", "/api/")]
    if len(generics) != 1:
        raise PatchRefused("expected_single_generic_api_location")
    generic = generics[0]
    assert generic.body_start is not None and generic.body_end is not None
    if any(node.words[0] in {"include", "location"} for node in generic.children):
        raise PatchRefused("unsupported_api_include_or_nested_location")
    if any(node.words[0] == "client_max_body_size" for node in generic.children):
        raise PatchRefused("unexpected_generic_api_size_limit")
    proxy_pass = [node for node in generic.children if node.words[0] == "proxy_pass"]
    if len(proxy_pass) != 1 or len(proxy_pass[0].words) != 2 or proxy_pass[0].body_start is not None:
        raise PatchRefused("expected_single_proxy_upstream")
    for node in locations:
        if node is generic:
            continue
        args = node.words[1:]
        if "uploads/proxy" in " ".join(args):
            raise PatchRefused("existing_upload_proxy_location")
        if len(args) == 2 and args[0] == "=" and re.fullmatch(UPLOAD_PATTERN, args[1]):
            raise PatchRefused("shadowing_exact_location")
        if len(args) == 2 and args[0] == "^~" and any(path.startswith(args[1]) for path in SAMPLE_PATHS):
            raise PatchRefused("shadowing_prefix_location")
        if node.start < generic.start and len(args) == 2 and args[0] in {"~", "~*"}:
            try:
                flags = re.IGNORECASE if args[0] == "~*" else 0
                matches = any(re.search(args[1], path, flags) for path in SAMPLE_PATHS)
            except re.error as exc:
                raise PatchRefused("unsupported_prior_regex_location") from exc
            if matches:
                raise PatchRefused("shadowing_regex_location")
    body = config[generic.body_start:generic.body_end]
    removals = []
    for node in generic.children:
        if len(node.words) >= 2 and node.words[0] == "proxy_set_header" and node.words[1].lower() in {"upgrade", "connection"}:
            removals.append(_directive_line_span(config, node))
    for start, end in reversed(removals):
        body = body[:start - generic.body_start] + body[end - generic.body_start:]
    line_start = config.rfind("\n", 0, generic.start) + 1
    indent = config[line_start:generic.start]
    if indent.strip():
        raise PatchRefused("unsupported_inline_api_location")
    body = body.strip("\n").rstrip() + "\n"
    insertion = (
        f"{indent}{PATCH_MARKER}\n"
        f"{indent}{UPLOAD_LOCATION} {{\n"
        f"{indent}  client_max_body_size 21m;\n"
        f"{body}"
        f"{indent}}}\n\n"
    )
    candidate = (config[:line_start] + insertion + config[line_start:]).encode("utf-8")
    # Only one insertion is allowed, including no normalization of existing bytes.
    assert candidate.replace(insertion.encode("utf-8"), b"", 1) == original
    assert len(_parse(candidate.decode("utf-8"))) == len(roots)
    return PatchResult(candidate, digest, hashlib.sha256(candidate).hexdigest(), len(candidate) - len(original))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        print(json.dumps({"ok": False, "error": "output_must_be_new_and_distinct"}))
        return 2
    try:
        patched = patch_config(args.input.read_bytes(), expected_sha256=args.expected_sha256)
        # Exclusive output creation prevents accidental overwrites during staging.
        with args.output.open("xb") as output:
            output.write(patched.content)
    except PatchRefused as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    except OSError:
        print(json.dumps({"ok": False, "error": "staging_io_failed"}))
        return 2
    print(json.dumps({"ok": True, "originalSha256": patched.original_sha256, "candidateSha256": patched.candidate_sha256, "insertedBytes": patched.inserted_bytes, "fileLimitBytes": 20 * 1024 * 1024, "gatewayEnvelopeBytes": 21 * 1024 * 1024}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
