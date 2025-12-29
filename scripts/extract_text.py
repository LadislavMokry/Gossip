#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys

CHAPTER_RE = re.compile(r"^(chapter|kapitola|book|part)\s+([0-9ivxlcdm]+)(\b.*)?$", re.IGNORECASE)


def detect_format(path, forced_format):
    if forced_format:
        return forced_format.lower()
    _, ext = os.path.splitext(path)
    return ext.lstrip('.').lower()


def read_text(path, fmt):
    if fmt == 'pdf':
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError('Missing dependency: pdfplumber') from exc
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or '')
        return "\n".join(parts)

    if fmt == 'docx':
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError('Missing dependency: python-docx') from exc
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    # Default: plain text
    with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
        return handle.read()


def chunk_by_words(text, max_words):
    words = text.split()
    if not words:
        return []
    chunks = []
    for idx in range(0, len(words), max_words):
        part = " ".join(words[idx:idx + max_words]).strip()
        if not part:
            continue
        chunks.append({
            'title': f'Part {len(chunks) + 1}',
            'text': part
        })
    return chunks


def split_by_chapters(text, default_title, max_words):
    lines = [line.strip() for line in text.splitlines()]
    sections = []
    current_title = default_title
    current_lines = []
    saw_heading = False

    def flush(title):
        nonlocal current_lines
        body = "\n".join([line for line in current_lines if line]).strip()
        if body:
            sections.append({
                'title': title,
                'text': body
            })
        current_lines = []

    for line in lines:
        if not line:
            continue
        if CHAPTER_RE.match(line):
            if current_lines:
                flush('Intro' if not saw_heading else current_title)
            current_title = line
            saw_heading = True
            continue
        current_lines.append(line)

    if current_lines:
        flush(current_title)

    if not sections:
        return chunk_by_words(text, max_words)

    return sections


def main():
    parser = argparse.ArgumentParser(description='Extract text from files and split by chapter headings.')
    parser.add_argument('--input', required=True, help='Path to input file')
    parser.add_argument('--format', default='', help='Override file format: pdf, docx, txt')
    parser.add_argument('--title', default='', help='Override document title')
    parser.add_argument('--max-words', type=int, default=2500, help='Chunk size when no headings found')
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f'Input file not found: {input_path}')

    fmt = detect_format(input_path, args.format)
    if fmt not in {'pdf', 'docx', 'txt'}:
        fmt = 'txt'

    text = read_text(input_path, fmt)
    if not text or not text.strip():
        raise RuntimeError('No text extracted from file')

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    doc_title = args.title.strip() or base_name or 'Manual Upload'

    sections = split_by_chapters(text, doc_title, args.max_words)

    payload = {
        'document_title': doc_title,
        'total_sections': len(sections),
        'sections': sections
    }

    print(json.dumps(payload, ensure_ascii=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        error_payload = {
            'error': str(exc)
        }
        print(json.dumps(error_payload, ensure_ascii=True), file=sys.stderr)
        sys.exit(1)
