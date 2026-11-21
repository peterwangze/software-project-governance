"""Local English and Chinese negation rules shared by governance claim checks."""

import re


DIRECT_PRE_MARKERS = (
    "not", "no", "does not", "do not", "is not", "are not", "isn't",
    "doesn't", "don't", "不是", "不等于", "不得", "不能", "不声明", "未",
    "未发现", "没有", "明确否定", "阻断", "拦截",
)
PREDICATE_MARKERS = (
    "does not claim", "do not claim", "not claim", "does not mean",
    "do not mean", "doesn't mean", "don't mean", "is not", "are not",
    "isn't", "no", "不是", "不等于", "不替代", "不得", "不能", "不声明",
    "未", "未发现", "没有", "avoid", "avoids", "避免", "明确否定", "阻断", "拦截",
)
POST_MARKERS = (
    "is not", "are not", "isn't", "not claimed", "not verified", "not proof",
    "不是", "不等于", "不得", "不能", "不声明", "未", "没有", "不可用",
    "不可发布", "仍不可用", "仍不可发布", "保守处置", "继续保留", "继续打开",
    "仍打开", "仍需", "阻断", "拦截", "过度声明", "肯定式过度声明",
)

def _claim_local_window(text, start, end):
    clause_start = max(
        (text.rfind(marker, 0, start) for marker in ";；.!?！？|:："),
        default=-1,
    ) + 1
    clause_ends = [text.find(marker, end) for marker in ";；.!?！？|:："]
    clause_end = min((pos for pos in clause_ends if pos >= 0), default=len(text))
    return text[clause_start:start], text[end:clause_end]


def _word_count(text):
    return len(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower()))


def _marker_positions(text, markers):
    lower = text.lower()
    positions = []
    for marker in markers:
        marker_lower = marker.lower()
        if re.search(r"[a-z0-9]", marker_lower):
            pattern = rf"(?<![a-z0-9]){re.escape(marker_lower)}(?![a-z0-9])"
            positions.extend(
                (match.start(), match.end(), marker_lower)
                for match in re.finditer(pattern, lower)
            )
        else:
            start = lower.find(marker_lower)
            while start != -1:
                positions.append((start, start + len(marker_lower), marker_lower))
                start = lower.find(marker_lower, start + len(marker_lower))
    return positions


def is_claim_negated(text, phrase, noun_claim_terms):
    """Every occurrence must be negated in its own clause under the caller's vocabulary."""
    lower = text.lower()
    claim_lower = phrase.lower()
    matches = list(re.finditer(re.escape(claim_lower), lower))
    if not matches:
        return False
    for match in matches:
        prefix, suffix = _claim_local_window(lower, match.start(), match.end())
        negated = False
        prefix_window = prefix[-96:]
        for _start, marker_end, _marker in _marker_positions(prefix_window, DIRECT_PRE_MARKERS):
            between = prefix_window[marker_end:]
            if not re.search(r"[,;；.!?！？|:：]", between) and _word_count(between) <= 2:
                negated = True
                break
        if not negated:
            for _start, marker_end, marker in _marker_positions(prefix, PREDICATE_MARKERS):
                between = prefix[marker_end:]
                if marker == "no":
                    if claim_lower not in noun_claim_terms:
                        continue
                    if not any(other_claim in between for other_claim in noun_claim_terms):
                        continue
                if _word_count(between) <= 36:
                    negated = True
                    break
        if not negated:
            suffix_head = suffix[:96]
            for marker_start, _end, _marker in _marker_positions(suffix_head, POST_MARKERS):
                between = suffix_head[:marker_start]
                if not re.search(r"[,;；.!?！？|:：]", between) and _word_count(between) <= 3:
                    negated = True
                    break
        if not negated:
            return False
    return True
