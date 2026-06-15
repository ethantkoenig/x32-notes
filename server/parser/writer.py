from __future__ import annotations

import re

_CH_RE = re.compile(r"^/ch/(\d{2})/(.+)$")


def _quote(token: str) -> str:
    if not token or " " in token or '"' in token:
        escaped = token.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return token


def channel_lines(ch_idx: int, raw: dict[str, list[str]]) -> list[str]:
    """Generate .scn text lines for one channel from its raw subpath → token dict."""
    prefix = f"/ch/{ch_idx:02d}/"
    return [
        " ".join([prefix + subpath] + [_quote(t) for t in tokens])
        for subpath, tokens in raw.items()
    ]


def merge_scene(source_text: str, patches: dict[int, dict[str, list[str]]]) -> str:
    """
    Return new .scn text with specified channels replaced.

    patches: {channel_index: raw_dict_from_chn_file}
    Lines for patched channels are removed and replaced at the end.
    All other lines (non-patched channels, blank lines, comments) are preserved.
    """
    out = []
    for line in source_text.splitlines():
        m = _CH_RE.match(line.strip())
        if m and int(m.group(1)) in patches:
            continue
        out.append(line)

    for ch_idx in sorted(patches):
        out.extend(channel_lines(ch_idx, patches[ch_idx]))

    result = "\n".join(out)
    if not result.endswith("\n"):
        result += "\n"
    return result
