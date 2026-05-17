"""Text extraction and cleaning utilities."""

import re
import string

import nltk
from docx import Document
from nltk.corpus import stopwords
from PyPDF2 import PdfReader

_nltk_ready = False


def _ensure_nltk():
    global _nltk_ready
    if not _nltk_ready:
        for resource in ("stopwords", "punkt", "punkt_tab"):
            try:
                nltk.data.find(f"corpora/{resource}" if resource == "stopwords" else f"tokenizers/{resource}")
            except LookupError:
                nltk.download(resource, quiet=True)
        _nltk_ready = True


def extract_text_from_file(uploaded_file) -> str:
    """Extract raw text from PDF or DOCX upload."""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
        return "\n".join(parts)
    if name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValueError("Unsupported file format. Use PDF or DOCX.")


def clean_text(text: str) -> set[str]:
    """Tokenize, normalize, and remove stopwords; returns unique word set."""
    _ensure_nltk()
    stop_words = set(stopwords.words("english"))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s+#.+]", " ", text)
    words = text.split()
    cleaned = set()
    for word in words:
        word = word.strip(string.punctuation)
        if word and word not in stop_words and len(word) > 2:
            if word.isalnum() or word.replace(".", "").isalnum():
                cleaned.add(word)
    return cleaned


def extract_keywords_from_jd(jd_text: str, max_keywords: int = 40) -> set[str]:
    """Extract meaningful keywords from job description."""
    _ensure_nltk()
    words = clean_text(jd_text)
    try:
        tokens = nltk.word_tokenize(jd_text.lower())
        bigrams = {" ".join(pair) for pair in nltk.bigrams(tokens) if len(pair) == 2}
        words.update(bg for bg in bigrams if len(bg) > 5)
    except Exception:
        pass
    role_terms = re.findall(r"[a-z][a-z0-9+.#]{2,}", jd_text.lower())
    words.update(t for t in role_terms if len(t) > 2)
    return set(list(words)[:max_keywords])
