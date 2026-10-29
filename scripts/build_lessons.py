# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.45", "pypdf>=4.0"]
# ///
"""Собирает бумажные уроки: lessons/*/lesson.html → lesson.pdf (А4) рядом.

Запуск из корня репозитория:
    uv run scripts/build_lessons.py [ПАПКА_УРОКА ...]

Без аргументов собирает все уроки и склеивает их в один файл для печати
lessons/all_lessons.pdf: сначала содержание (lessons/contents), потом уроки по номерам.
Печатает путь к каждому PDF.
Коды возврата: 0 — все собраны, 1 — урок не найден.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfWriter

LESSONS = Path(__file__).resolve().parent.parent / "lessons"
CONTENTS = "contents"  # папка листа содержания — в общем файле идёт первой


def lesson_files(args: list[str]) -> list[Path]:
    """Находит lesson.html по аргументам командной строки.

    Args:
        args: Папки уроков (путь или имя внутри lessons/). Пусто — все уроки.

    Returns:
        Список путей к lesson.html.

    Raises:
        FileNotFoundError: В указанной папке нет lesson.html.
    """
    if not args:
        return sorted(LESSONS.glob("*/lesson.html"))
    found = []
    for arg in args:
        folder = Path(arg) if Path(arg).is_dir() else LESSONS / arg
        html = folder / "lesson.html"
        if not html.is_file():
            raise FileNotFoundError(html)
        found.append(html.resolve())
    return found


def build(htmls: list[Path]) -> list[Path]:
    """Печатает каждый lesson.html в PDF формата А4 одним запуском браузера.

    Args:
        htmls: Пути к lesson.html.

    Returns:
        Пути к собранным lesson.pdf.
    """
    pdfs = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")  # системный Chrome, без скачивания
        page = browser.new_page()
        for html in htmls:
            pdf = html.with_suffix(".pdf")
            page.goto(html.as_uri())
            page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
            pdfs.append(pdf)
        browser.close()
    return pdfs


def merge(pdfs: list[Path]) -> Path:
    """Склеивает PDF уроков в один файл для печати: содержание первым.

    Args:
        pdfs: Пути к lesson.pdf всех уроков.

    Returns:
        Путь к lessons/all_lessons.pdf.
    """
    ordered = sorted(pdfs, key=lambda pdf: (pdf.parent.name != CONTENTS, pdf.parent.name))
    out = LESSONS / "all_lessons.pdf"
    writer = PdfWriter()
    for pdf in ordered:
        writer.append(str(pdf))
    with out.open("wb") as f:
        writer.write(f)
    return out


def main() -> int:
    """Точка входа: собирает уроки и печатает пути к PDF."""
    try:
        htmls = lesson_files(sys.argv[1:])
    except FileNotFoundError as err:
        print(f"нет урока: {err}", file=sys.stderr)
        return 1
    pdfs = build(htmls)
    for pdf in pdfs:
        print(pdf)
    if not sys.argv[1:]:
        print(merge(pdfs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
