import math
import re
from collections import Counter


SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{2,}")
STOPWORDS = {
    "это", "как", "что", "для", "или", "есть", "при", "она", "они", "the", "and",
    "with", "from", "that", "this", "have", "быть", "его", "её", "так", "was", "are",
    "вот", "если", "если", "потому", "очень", "просто", "только", "когда", "тоже",
    "здесь", "туда", "тогда", "вообще", "который", "которая", "которые", "этот",
    "того", "можно", "будет", "чтобы", "there", "about", "into", "your", "their",
    "ну", "или", "она", "они", "оно", "мне", "меня", "мной", "тебя", "тебе", "тоже",
    "вам", "вас", "вами", "нами", "наша", "наши", "наш", "ваш", "ваши", "ваша",
    "всё", "все", "где", "тут", "там", "какой", "какая", "какие", "такой", "такая",
    "такие", "какого", "какому", "потом", "после", "перед", "через", "между", "себя",
    "себе", "свой", "свои", "своего", "свою", "своим", "сам", "сама", "сами", "мой",
    "моя", "мои", "твой", "твоя", "твои", "нашли", "были", "было", "будто", "пока",
    "либо", "даже", "ещё", "еще", "лишь", "прям", "очень", "вообще", "типа", "кстати",
    "причем", "например", "говоришь", "говорит", "котором", "которую", "которых",
    "which", "therefore", "really", "very", "just", "into", "onto", "than", "then",
    "нет", "ага", "ладно", "короче", "сейчас", "прямо", "честно", "кстати", "знаете",
    "сказать", "говорю", "говорить", "просто", "вообще", "именно", "почему", "какая-то",
    "какой-то", "какие-то", "каком-то", "какую-то", "очевидно", "реально", "сильно",
    "этом", "этой", "эти", "этим", "этого", "самом", "деле", "числе", "общем", "раз",
    "про", "кстати", "прям", "вроде", "всегда", "потом", "знаю",
}
FILLER_WORDS = {
    "ну", "ээ", "эм", "ага", "мм", "м", "а", "и", "да", "нет", "вот", "типа", "как",
}


def split_sentences(text: str) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    return [item.strip() for item in SENTENCE_RE.split(text) if item.strip()]


def filtered_words(text: str) -> list[str]:
    prepared = []
    for word in WORD_RE.findall(text):
        normalized = word.lower()
        if len(normalized) < 3 or normalized in STOPWORDS:
            continue
        prepared.append(normalized)
    return prepared


def normalize_segment_text(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"\s+([,.;:!?…])", r"\1", text)
    text = re.sub(r"([,.;:!?…])([^\s])", r"\1 \2", text)
    return text.strip()


def is_filler_segment(text: str) -> bool:
    tokens = [token.lower() for token in re.findall(r"[A-Za-zА-Яа-яЁё]+", text)]
    if len(tokens) < 3:
        return False
    return all(token in FILLER_WORDS for token in tokens)


def sanitize_segments(segments: list[dict]) -> list[dict]:
    cleaned = []
    previous_text = ""
    for segment in segments:
        text = normalize_segment_text(str(segment.get("text", "")))
        if not text or is_filler_segment(text):
            continue
        if text == previous_text:
            continue
        cleaned.append(
            {
                "start": round(float(segment.get("start", 0.0)), 2),
                "end": round(float(segment.get("end", 0.0)), 2),
                "text": text,
            }
        )
        previous_text = text
    return cleaned


def extract_topic_keywords(text: str, max_items: int = 8) -> list[str]:
    freq = Counter(filtered_words(text))
    return [word for word, _ in freq.most_common(max_items)]


def summarize_text(text: str, max_sentences: int = 5) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return "Не удалось построить summary: транскрипт пустой."
    if len(sentences) <= max_sentences:
        return "\n\n".join(sentences)

    freq = Counter(filtered_words(text))
    if not freq:
        return "\n\n".join(sentences[:max_sentences])

    scored = []
    for idx, sentence in enumerate(sentences):
        sent_words = filtered_words(sentence)
        unique_words = set(sent_words)
        if len(unique_words) < 3 or len(sent_words) < 5:
            score = 0.0
        else:
            score = sum(freq[w] for w in sent_words) / math.sqrt(len(unique_words))
        scored.append((idx, score, sentence))

    selected_top = [item for item in sorted(scored, key=lambda x: x[1], reverse=True) if item[1] > 0][:max_sentences]
    if not selected_top:
        return "\n\n".join(sentences[:max_sentences])

    selected = sorted(selected_top, key=lambda x: x[0])
    return "\n\n".join(sentence for _, _, sentence in selected)


def build_highlight_analysis(text: str, duration: float, keywords: list[str]) -> str:
    if keywords:
        return f"Фрагмент длиной {int(round(duration))} сек. В центре внимания: {', '.join(keywords[:4])}."
    return f"Семантически насыщенный фрагмент длиной {int(round(duration))} сек."


def build_window_candidate(
    segments: list[dict],
    start_index: int,
    *,
    min_duration: int,
    target_duration: int,
    max_duration: int,
    global_freq: Counter,
) -> dict | None:
    start = float(segments[start_index]["start"])
    text_parts: list[str] = []
    options: list[tuple[float, int, float, str]] = []

    for end_index in range(start_index, len(segments)):
        segment = segments[end_index]
        text = str(segment.get("text", "")).strip()
        if text:
            text_parts.append(text)
        end = float(segment.get("end", start))
        duration = max(0.0, end - start)
        candidate_text = " ".join(text_parts).strip()
        if duration >= min_duration and candidate_text:
            options.append((abs(duration - target_duration), end_index, duration, candidate_text))
        if duration >= max_duration:
            break

    if not options:
        return None

    _, end_index, duration, candidate_text = min(options, key=lambda item: item[0])
    words = filtered_words(candidate_text)
    if len(words) < 25:
        return None

    window_freq = Counter(words)
    top_keywords = [word for word, _ in window_freq.most_common(6)]
    centrality_score = sum(global_freq[word] for word in set(words)) / math.sqrt(len(words))
    keyword_bonus = sum(window_freq[word] for word in top_keywords[:3]) / max(duration, 1.0)
    score = centrality_score + keyword_bonus * 12

    return {
        "start_index": start_index,
        "end_index": end_index,
        "start": round(start, 2),
        "end": round(float(segments[end_index]["end"]), 2),
        "text": candidate_text,
        "score": round(float(score), 2),
        "analysis": build_highlight_analysis(candidate_text, duration, top_keywords),
    }


def overlap_ratio(candidate: dict, selected: dict) -> float:
    overlap_start = max(float(candidate["start"]), float(selected["start"]))
    overlap_end = min(float(candidate["end"]), float(selected["end"]))
    overlap = max(0.0, overlap_end - overlap_start)
    candidate_duration = max(1.0, float(candidate["end"]) - float(candidate["start"]))
    selected_duration = max(1.0, float(selected["end"]) - float(selected["start"]))
    return max(overlap / candidate_duration, overlap / selected_duration)


def choose_highlights(
    segments: list[dict],
    max_items: int = 3,
    *,
    min_duration: int = 60,
    target_duration: int = 75,
    max_duration: int = 90,
) -> list[dict]:
    if not segments:
        return []

    full_text = " ".join(str(segment.get("text", "")).strip() for segment in segments)
    global_freq = Counter(filtered_words(full_text))
    if not global_freq:
        return []

    total_duration = max(0.0, float(segments[-1].get("end", 0.0)) - float(segments[0].get("start", 0.0)))
    effective_min = min_duration if total_duration >= min_duration else max(20, int(total_duration))
    effective_target = min(target_duration, max_duration, max(effective_min, int(total_duration) if total_duration else target_duration))
    effective_max = max(max_duration, effective_min)

    candidates = []
    for start_index in range(len(segments)):
        candidate = build_window_candidate(
            segments,
            start_index,
            min_duration=effective_min,
            target_duration=effective_target,
            max_duration=effective_max,
            global_freq=global_freq,
        )
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return []

    selected = []
    for candidate in sorted(candidates, key=lambda item: item["score"], reverse=True):
        if any(overlap_ratio(candidate, existing) > 0.35 for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= max_items:
            break

    selected = sorted(selected, key=lambda item: item["start"])
    return [{"rank": index + 1, **item} for index, item in enumerate(selected)]
