"""Bluesky投稿の書記素数を安全に制限するユーティリティ。"""

import unicodedata


_VARIATION_SELECTORS = {chr(codepoint) for codepoint in range(0xFE00, 0xFE10)}
_EMOJI_MODIFIERS = {chr(codepoint) for codepoint in range(0x1F3FB, 0x1F400)}
_ZWJ = "\u200d"


def _graphemes(text):
    clusters = []
    current = ""
    regional_count = 0

    for char in text:
        is_mark = (
            unicodedata.combining(char) != 0
            or char in _VARIATION_SELECTORS
            or char in _EMOJI_MODIFIERS
            or char == "\u20e3"
        )

        if not current:
            current = char
            regional_count = 1 if 0x1F1E6 <= ord(char) <= 0x1F1FF else 0
        elif is_mark or char == _ZWJ or current.endswith(_ZWJ):
            current += char
        elif regional_count == 1 and 0x1F1E6 <= ord(char) <= 0x1F1FF:
            current += char
            regional_count = 2
        else:
            clusters.append(current)
            current = char
            regional_count = 1 if 0x1F1E6 <= ord(char) <= 0x1F1FF else 0

    if current:
        clusters.append(current)
    return clusters


def limit_graphemes(text, maximum=300):
    """Return text with at most ``maximum`` user-visible characters."""
    clusters = _graphemes(text)
    if len(clusters) <= maximum:
        return text
    if maximum <= 0:
        return ""
    suffix = "…"
    kept = max(0, maximum - 1)
    return "".join(clusters[:kept]).rstrip() + suffix