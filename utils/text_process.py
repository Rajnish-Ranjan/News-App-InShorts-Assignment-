import re
from urllib.parse import urlparse

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "if",
    "in",
    "into",
    "is",
    "it",
    "no",
    "not",
    "of",
    "on",
    "or",
    "such",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "will",
    "with",
    "what",
    "why",
    "where",
    "when",
    "who",
    "how",
    "give",
    "me",
    "show",
    "tell",
    "news",
    "about",
    "latest",
    "some",
    "any",
    "around",
    "top",
}


def preprocess_search_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"[^\w\s]", " ", text).lower()

    words = text.split()
    filtered_words = [
        word for word in words if word not in STOP_WORDS and len(word) > 1
    ]

    return " ".join(filtered_words)

def extract_url_tokens(url: str) -> list[str]:
    if not url:
        return []
    parsed_url = urlparse(url)
    return re.findall(r"[a-zA-Z0-9]+", parsed_url.path)

