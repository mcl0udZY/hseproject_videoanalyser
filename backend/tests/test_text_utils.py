from app.utils.text import (
    choose_highlights,
    extract_topic_keywords,
    filtered_words,
    normalize_segment_text,
    sanitize_segments,
    split_sentences,
    summarize_text,
)


def test_split_sentences():
    txt = "Первое предложение. Второе предложение! Третье?"
    res = split_sentences(txt)

    assert res == ["Первое предложение.", "Второе предложение!", "Третье?"]


def test_filtered_words_removes_stopwords():
    txt = "Это видео анализирует интерфейс и транскрипцию видео"
    res = filtered_words(txt)

    assert "это" not in res
    assert "видео" in res
    assert "интерфейс" in res


def test_normalize_segment_text():
    txt = "  Привет   ,мир !  Это   тест. "
    res = normalize_segment_text(txt)

    assert res == "Привет, мир! Это тест."


def test_sanitize_segments_removes_empty_fillers_and_duplicates():
    seg = [
        {"start": 0, "end": 1, "text": "  Первый   фрагмент. "},
        {"start": 1, "end": 2, "text": "Первый фрагмент."},
        {"start": 2, "end": 3, "text": ""},
        {"start": 3, "end": 4, "text": "ну типа вот"},
        {"start": 4, "end": 5, "text": "Второй фрагмент."},
    ]

    res = sanitize_segments(seg)

    assert len(res) == 2
    assert res[0]["text"] == "Первый фрагмент."
    assert res[1]["text"] == "Второй фрагмент."


def test_summarize_text_returns_limited_summary():
    txt = (
        "Система загружает видео и создает задачу. "
        "После этого выполняется транскрибация речи. "
        "Затем формируется краткое содержание. "
        "Пользователь видит результат в веб-интерфейсе. "
        "Интерфейс показывает статус обработки и готовые файлы."
    )

    res = summarize_text(txt, max_sentences=2)

    assert isinstance(res, str)
    assert len(res) > 0
    assert len(res.split("\n\n")) <= 2


def test_extract_topic_keywords():
    txt = "Видео анализ видео транскрипт summary интерфейс интерфейс"

    res = extract_topic_keywords(txt, max_items=3)

    assert "видео" in res
    assert "интерфейс" in res


def test_choose_highlights_returns_ranked_items():
    segments = []

    for i in range(8):
        text = (
            "видео анализ алгоритм транскрипция summary интерфейс "
            "пользователь задача обработка результат "
        ) * 4

        segments.append(
            {
                "start": i * 10,
                "end": i * 10 + 10,
                "text": f"{text} номер {i}",
            }
        )

    res = choose_highlights(
        segments,
        max_items=2,
        min_duration=20,
        target_duration=30,
        max_duration=40,
    )

    assert len(res) > 0
    assert len(res) <= 2
    assert res[0]["rank"] == 1
    assert res[0]["start"] < res[0]["end"]
    assert "text" in res[0]
