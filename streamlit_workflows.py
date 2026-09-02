from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import streamlit as st

try:
    import backend
    BACKEND_IMPORT_ERROR = ""
except Exception as exc:
    backend = None
    BACKEND_IMPORT_ERROR = str(exc)

try:
    from better_profanity import profanity
    profanity.load_censor_words()
except Exception:
    profanity = None

try:
    import docx
except Exception:
    docx = None

try:
    import torch
except Exception:
    torch = None

DEFAULT_TOXICITY_THRESHOLD = 0.75
MIN_TOXICITY_WORD_COUNT = 3
MEDIA_TRANSCRIPT_REPLACEMENT = "****"
MEDIA_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav", ".m4a")
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v")
TEXT_EXTENSIONS = (".txt", ".docx")
ASR_MODELS = {
    "tiny.en": "tiny.en",
    "base.en": "base.en",
}
RATING_PRESETS = ["Default", "PG", "PG-13", "R", "NC-17"]

LEET_TRANSLATION = str.maketrans({"0": "o", "1": "i", "!": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "$": "s", "@": "a", "|": "i", "^": "a"})
TOKEN_RE = re.compile(r"https?://[^\s]+|www\.[^\s]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|[A-Za-z0-9_!$|@^]+(?:['-][A-Za-z0-9_!$|@^]+)*|\d+(?:[.,]\d+)*|\s+|[^\w\s]", re.UNICODE)
SENTENCE_RE = re.compile(r"\S.*?(?:[.!?]+(?=\s|$)|$)", re.DOTALL)
CONTRACTIONS = {
    "ain't": "am not", "aren't": "are not", "can't": "cannot", "couldn't": "could not", "didn't": "did not",
    "doesn't": "does not", "don't": "do not", "hadn't": "had not", "hasn't": "has not", "haven't": "have not",
    "he'd": "he would", "he'll": "he will", "he's": "he is", "i'd": "i would", "i'll": "i will", "i'm": "i am",
    "i've": "i have", "isn't": "is not", "it's": "it is", "let's": "let us", "mightn't": "might not", "mustn't": "must not",
    "shan't": "shall not", "she'd": "she would", "she'll": "she will", "she's": "she is", "shouldn't": "should not",
    "that's": "that is", "there's": "there is", "they'd": "they would", "they'll": "they will", "they're": "they are",
    "they've": "they have", "wasn't": "was not", "we'd": "we would", "we'll": "we will", "we're": "we are", "we've": "we have",
    "weren't": "were not", "what's": "what is", "won't": "will not", "wouldn't": "would not", "you'd": "you would",
    "you'll": "you will", "you're": "you are", "you've": "you have",
}
STOPWORDS = set("a an and are as at be but by for from has have he her his i if in is it its me my not of on or our she that the their them they this to us was we were with you your".split())
PRONOUNS = set("i me you he him she her it we us they them".split())
DETERMINERS = set("a an the this that these those my your his her its our their".split())
PREPOSITIONS = set("about above after against at before between by for from in into of on to under with without".split())
CONJUNCTIONS = set("and but or nor for yet so although because while".split())
AUXILIARIES = set("am are be been being can could did do does had has have is may might must shall should was were will would".split())

TOXICITY_MODEL = None
TOXICITY_TOKENIZER = None
TOXICITY_DEVICE = torch.device("cuda" if torch is not None and torch.cuda.is_available() else "cpu") if torch is not None else None

@dataclass
class TokenAnalysis:
    index: int
    text: str
    token_type: str
    normalized: str
    lemma: str
    pos_guess: str
    start: int
    end: int
    length: int
    shape: str
    is_stopword: bool
    is_whitelisted: bool
    is_blacklisted: bool
    is_profane: bool
    is_obfuscated: bool
    detection_source: str
    severity_category: str = "NONE"
    replacement: str = ""
    is_censored: bool = False

@dataclass
class SentenceAnalysis:
    index: int
    text: str
    start: int
    end: int
    word_count: int
    replacement: str = ""


def emit(callback: Any, message: Any) -> None:
    if callback is None:
        return
    if hasattr(callback, "emit"):
        callback.emit(message)
    elif callable(callback):
        callback(message)


def read_text_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252", "utf-16"):
            try:
                with open(file_path, "r", encoding=encoding) as handle:
                    return handle.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                return ""
    if ext == ".docx" and docx is not None:
        try:
            document = docx.Document(file_path)
            return "\n".join(p.text for p in document.paragraphs if p.text)
        except Exception:
            return ""
    return ""


def normalize_unicode_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    for source, target in {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\u200b": "", "\ufeff": ""}.items():
        text = text.replace(source, target)
    return text


def normalize_for_profanity(word: str) -> str:
    word = normalize_unicode_text(word).lower().translate(LEET_TRANSLATION).replace("ph", "f")
    word = re.sub(r"(.)\1{2,}", r"\1\1", word)
    word = re.sub(r"[^a-z]", "", word)
    return word if len(word) > 1 else ""


def expand_contractions(text: str) -> str:
    if not text:
        return ""
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(CONTRACTIONS, key=len, reverse=True)) + r")\b", re.IGNORECASE)
    def replace(match: re.Match) -> str:
        source = match.group(0)
        value = CONTRACTIONS.get(source.lower(), source)
        return value[:1].upper() + value[1:] if source[:1].isupper() else value
    return pattern.sub(replace, text)

def preprocess_text(text: str, options: Optional[Dict[str, bool]] = None) -> Tuple[str, List[str]]:
    options = options or {}
    processed = text or ""
    steps: List[str] = []
    if options.get("normalize_unicode", True):
        processed = normalize_unicode_text(processed)
        steps.append("unicode_normalization")
    if options.get("expand_contractions", False):
        processed = expand_contractions(processed)
        steps.append("contraction_expansion")
    if options.get("remove_urls", False):
        processed = re.sub(r"https?://\S+|www\.\S+", "", processed)
        steps.append("url_removal")
    if options.get("remove_emails", False):
        processed = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "", processed)
        steps.append("email_removal")
    if options.get("casefold", False):
        processed = processed.casefold()
        steps.append("casefold")
    if options.get("compact_whitespace", False):
        processed = re.sub(r"\s+", " ", processed).strip()
        steps.append("whitespace_compaction")
    return processed, steps


def tokenize_text(text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in TOKEN_RE.finditer(text or "")]


def split_sentences(text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in SENTENCE_RE.finditer(text or "") if m.group(0).strip()]


def load_word_list(text: str) -> Set[str]:
    return {normalized for normalized in (normalize_for_profanity(part) for part in re.findall(r"\S+", text or "")) if normalized}


PROFANITY_DICTIONARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profanity_dictionary.json")

def load_profanity_dictionary() -> Dict[str, Any]:
    if os.path.exists(PROFANITY_DICTIONARY_PATH):
        try:
            with open(PROFANITY_DICTIONARY_PATH, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            print(f"Failed to load profanity_dictionary.json: {exc}")
    return {}

PROFANITY_DICTIONARY = load_profanity_dictionary()

PROFANITY_SEVERITY_MAP: Dict[str, str] = {}
if PROFANITY_DICTIONARY:
    for cat_name, cat_data in PROFANITY_DICTIONARY.get("categories", {}).items():
        for w in cat_data.get("words", []):
            PROFANITY_SEVERITY_MAP[w.lower()] = cat_name


def get_rating_preset_whitelist(preset: str) -> Set[str]:
    categories = PROFANITY_DICTIONARY.get("categories", {})
    mild = set(categories.get("MILD", {}).get("words", []))
    moderate = set(categories.get("MODERATE", {}).get("words", []))
    strong = set(categories.get("STRONG", {}).get("words", []))
    
    if preset == "PG-13":
        return {normalize_for_profanity(w) for w in mild if normalize_for_profanity(w)}
    elif preset == "R":
        return {normalize_for_profanity(w) for w in (mild | moderate) if normalize_for_profanity(w)}
    elif preset == "NC-17":
        return {normalize_for_profanity(w) for w in (mild | moderate | strong) if normalize_for_profanity(w)}
    return set()


def safe_contains_profanity(value: str) -> bool:
    if profanity is None or not value:
        return False
    try:
        return bool(profanity.contains_profanity(value))
    except Exception:
        return False


def classify_profanity_token(word: str, whitelist: Set[str], blacklist: Set[str], use_obfuscation: bool, use_standard: bool = True) -> Dict[str, Any]:
    normalized = normalize_for_profanity(word)
    result = {
        "normalized": normalized,
        "is_profane": False,
        "is_obfuscated": False,
        "is_whitelisted": False,
        "is_blacklisted": False,
        "detection_source": "clean",
        "severity_category": PROFANITY_SEVERITY_MAP.get(normalized, PROFANITY_SEVERITY_MAP.get((word or "").lower(), "NONE")),
    }
    if normalized and normalized in whitelist:
        result["is_whitelisted"] = True
        result["detection_source"] = "whitelist"
        result["severity_category"] = "WHITELISTED"
        return result

    if normalized and normalized in blacklist:
        result["is_profane"] = True
        result["is_blacklisted"] = True
        result["detection_source"] = "blacklist"
        if result["severity_category"] == "NONE":
            result["severity_category"] = "CUSTOM_BLACKLIST"
        return result

    original_hit = use_standard and safe_contains_profanity(word)
    normalized_hit = use_obfuscation and normalized and safe_contains_profanity(normalized)
    if original_hit:
        result["is_profane"] = True
        result["detection_source"] = "lexicon"
    elif normalized_hit:
        result["is_profane"] = True
        result["is_obfuscated"] = True
        result["detection_source"] = "obfuscated"

    plain_lower = re.sub(r"[^a-z]", "", (word or "").lower())
    if result["is_profane"] and normalized and normalized != plain_lower:
        result["is_obfuscated"] = True
    return result


def format_censored_word(word: str, style: str, custom_replacement: str) -> str:
    if style == "A":
        return "*" * len(word)
    if style == "B":
        return word[0] + ("*" * max(1, len(word) - 1)) if word else "*"
    if style == "D":
        return custom_replacement
    return "****"


def classify_token_type(token: str) -> str:
    if token.isspace():
        return "whitespace"
    if re.match(r"^(?:https?://|www\.)", token, re.IGNORECASE):
        return "url"
    if re.match(r"^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$", token):
        return "email"
    if re.match(r"^\d+(?:[.,]\d+)*$", token):
        return "number"
    if re.search(r"[A-Za-z0-9_!$|@^]", token):
        return "word"
    if re.match(r"^[^\w\s]+$", token):
        return "punctuation"
    return "symbol"


def simple_lemma(token: str, normalized: str = "") -> str:
    word = normalized or normalize_for_profanity(token)
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ied"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def guess_pos(token: str, token_type: str, normalized: str) -> str:
    if token_type == "whitespace":
        return "SPACE"
    if token_type == "punctuation":
        return "PUNCT"
    if token_type == "number":
        return "NUM"
    if token_type == "url":
        return "URL"
    if token_type == "email":
        return "EMAIL"
    if token_type != "word":
        return "SYM"
    word = normalized or token.lower()
    if word in PRONOUNS:
        return "PRON"
    if word in DETERMINERS:
        return "DET"
    if word in PREPOSITIONS:
        return "ADP"
    if word in CONJUNCTIONS:
        return "CONJ"
    if word in AUXILIARIES:
        return "AUX"
    if word.endswith("ly"):
        return "ADV"
    if word.endswith(("ing", "ed", "ize", "ise")):
        return "VERB"
    if word.endswith(("ous", "ful", "able", "ible", "al", "ive", "less", "ic")):
        return "ADJ"
    if token[:1].isupper() and token[1:].islower():
        return "PROPN"
    return "NOUN"


def token_shape(token: str) -> str:
    raw = []
    for char in token:
        if char.isupper():
            raw.append("X")
        elif char.islower():
            raw.append("x")
        elif char.isdigit():
            raw.append("d")
        elif char.isspace():
            raw.append("_")
        else:
            raw.append(char)
    compressed = []
    for item in raw:
        if not compressed or compressed[-1] != item:
            compressed.append(item)
    return "".join(compressed)


def analyze_tokens(text: str, whitelist: Set[str], blacklist: Set[str], use_obfuscation: bool, use_standard: bool) -> List[TokenAnalysis]:
    rows: List[TokenAnalysis] = []
    for index, (token, start, end) in enumerate(tokenize_text(text)):
        token_type = classify_token_type(token)
        normalized = normalize_for_profanity(token) if token_type == "word" else ""
        info = classify_profanity_token(token, whitelist, blacklist, use_obfuscation, use_standard) if token_type == "word" else {
            "is_profane": False, "is_obfuscated": False, "is_whitelisted": False, "is_blacklisted": False, "detection_source": "clean"
        }
        rows.append(TokenAnalysis(
            index=index,
            text=token,
            token_type=token_type,
            normalized=normalized,
            lemma=simple_lemma(token, normalized) if token_type == "word" else "",
            pos_guess=guess_pos(token, token_type, normalized),
            start=start,
            end=end,
            length=len(token),
            shape=token_shape(token),
            is_stopword=normalized in STOPWORDS,
            is_whitelisted=bool(info["is_whitelisted"]),
            is_blacklisted=bool(info["is_blacklisted"]),
            is_profane=bool(info["is_profane"]),
            is_obfuscated=bool(info["is_obfuscated"]),
            detection_source=str(info["detection_source"]),
            severity_category=str(info.get("severity_category", "NONE")),
        ))
    return rows

def analyze_sentences(text: str) -> List[SentenceAnalysis]:
    sentences: List[SentenceAnalysis] = []
    for index, (sentence, start, end) in enumerate(split_sentences(text), start=1):
        words = [token for token, _, _ in tokenize_text(sentence) if classify_token_type(token) == "word"]
        sentences.append(SentenceAnalysis(
            index=index,
            text=sentence.strip(),
            start=start,
            end=end,
            word_count=len(words),
        ))
    return sentences


def summarize_text(raw_text: str, processed_text: str, cleaned_text: str, tokens: Sequence[TokenAnalysis], sentences: Sequence[SentenceAnalysis], preprocessing_steps: Sequence[str]) -> Dict[str, Any]:
    word_tokens = [token for token in tokens if token.token_type == "word"]
    terms = [token.normalized for token in word_tokens if token.normalized]
    term_counts = Counter(terms)
    pos_counts = Counter(token.pos_guess for token in word_tokens)
    profane = [token for token in word_tokens if token.is_profane]
    avg_len = sum(len(term) for term in terms) / len(terms) if terms else 0.0
    return {
        "raw_characters": len(raw_text),
        "processed_characters": len(processed_text),
        "cleaned_characters": len(cleaned_text),
        "word_count": len(word_tokens),
        "unique_terms": len(term_counts),
        "lexical_diversity": round(len(term_counts) / len(terms), 4) if terms else 0.0,
        "average_word_length": round(avg_len, 2),
        "sentence_count": len(sentences),
        "profane_word_count": len(profane),
        "obfuscated_word_count": sum(1 for token in profane if token.is_obfuscated),
        "blacklist_hits": sum(1 for token in profane if token.is_blacklisted),
        "whitelist_hits": sum(1 for token in word_tokens if token.is_whitelisted),
        "url_count": sum(1 for token in tokens if token.token_type == "url"),
        "email_count": sum(1 for token in tokens if token.token_type == "email"),
        "number_count": sum(1 for token in tokens if token.token_type == "number"),
        "stopword_count": sum(1 for token in word_tokens if token.is_stopword),
        "preprocessing_steps": list(preprocessing_steps),
        "top_terms": term_counts.most_common(25),
        "pos_counts": dict(pos_counts),
    }


def process_text_content(raw_text: str, options: Dict[str, Any], file_path: str = "", progress_callback: Any = None) -> Dict[str, Any]:
    if not raw_text or not raw_text.strip():
        raise ValueError("No text provided.")
    rating_preset = options.get("rating_preset", "Default")
    preset_whitelist = get_rating_preset_whitelist(rating_preset)
    whitelist = load_word_list(options.get("whitelist_text", "")) | preset_whitelist
    blacklist = load_word_list(options.get("blacklist_text", ""))
    if preset_whitelist:
        emit(progress_callback, f"Rating preset [{rating_preset}] applied ({len(preset_whitelist)} whitelisted words).")
    emit(progress_callback, f"Loaded {len(whitelist)} total whitelist word(s).")
    emit(progress_callback, f"Loaded {len(blacklist)} blacklist word(s).")
    if profanity is None and (options.get("clean_standard") or options.get("clean_obfuscated")):
        emit(progress_callback, "better_profanity is unavailable; custom blacklist still works.")

    processed_text, preprocessing_steps = preprocess_text(raw_text, options.get("preprocess", {}))
    clean_standard = bool(options.get("clean_standard", True))
    clean_obfuscated = bool(options.get("clean_obfuscated", True))
    style = options.get("censor_style", "A")
    custom = options.get("custom_replacement", "****")

    emit(progress_callback, 20)
    tokens = analyze_tokens(processed_text, whitelist, blacklist, clean_obfuscated, clean_standard)
    parts: List[str] = []
    for token in tokens:
        if token.token_type == "word" and (clean_standard or clean_obfuscated) and token.is_profane:
            token.replacement = format_censored_word(token.text, style, custom)
            token.is_censored = True
            parts.append(token.replacement)
        else:
            parts.append(token.text)
    cleaned_text = "".join(parts)

    emit(progress_callback, 50)
    sentences = analyze_sentences(cleaned_text)

    emit(progress_callback, 80)
    output_path = None
    if file_path and os.path.exists(file_path):
        base_name, _ = os.path.splitext(file_path)
        output_path = f"{base_name}_CLEANED.txt"
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(cleaned_text)
        emit(progress_callback, f"Cleaned text saved to: {output_path}")

    final_sentences = analyze_sentences(cleaned_text)
    stats = summarize_text(raw_text, processed_text, cleaned_text, tokens, final_sentences, preprocessing_steps)
    flags = []
    if stats["profane_word_count"]:
        flags.append(f"Lexicon/obfuscation censor applied ({stats['profane_word_count']} word(s)).")
    if not flags:
        flags.append("No flags detected.")

    summary = (
        "Cleaning Complete!\n\n"
        f"Original Length: {len(raw_text)} characters\n"
        f"Cleaned Length: {len(cleaned_text)} characters\n"
        f"Words: {stats['word_count']}\n"
        f"Unique Terms: {stats['unique_terms']}\n"
        f"Profanity Hits: {stats['profane_word_count']}\n\n"
        f"{'Output File Saved: ' + output_path if output_path else 'Results displayed in the app.'}\n\n"
        "Detections:\n- " + "\n- ".join(flags)
    )
    emit(progress_callback, 100)
    return {
        "raw_text": raw_text,
        "processed_text": processed_text,
        "cleaned_text": cleaned_text,
        "summary_message": summary,
        "output_path": output_path,
        "flags": flags,
        "tokens": [asdict(token) for token in tokens],
        "word_tokens": [asdict(token) for token in tokens if token.token_type == "word"],
        "sentences": [asdict(sentence) for sentence in final_sentences],
        "stats": stats,
        "flagged_tokens": [asdict(token) for token in tokens if token.is_profane],
    }


def process_text_file(file_path: str, options: Dict[str, Any], progress_callback: Any = None) -> Dict[str, Any]:
    raw_text = read_text_file(file_path)
    if not raw_text:
        raise ValueError("File is empty or could not be read.")
    return process_text_content(raw_text, options, file_path, progress_callback)

def require_backend() -> Any:
    if backend is None:
        raise RuntimeError(f"The media backend could not be imported: {BACKEND_IMPORT_ERROR}")
    return backend


def save_uploaded_file(uploaded_file: Any, suffix_dir: str = "profanity_cleaner") -> str:
    suffix = Path(uploaded_file.name).suffix
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(uploaded_file.name).stem).strip("._") or "upload"
    temp_dir = tempfile.mkdtemp(prefix=f"{suffix_dir}_")
    path = os.path.join(temp_dir, f"{stem}{suffix}")
    with open(path, "wb") as handle:
        handle.write(uploaded_file.getbuffer())
    return path


def save_uploaded_files(uploaded_files: Any, suffix_dir: str = "profanity_cleaner") -> List[str]:
    if not uploaded_files:
        return []
    files = uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]
    return [save_uploaded_file(f, suffix_dir) for f in files]


def format_time_srt(ms: int) -> str:
    hours = int(ms / 3600000)
    ms -= hours * 3600000
    minutes = int(ms / 60000)
    ms -= minutes * 60000
    seconds = int(ms / 1000)
    ms -= seconds * 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def media_log_summary(log: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    profanity_count = sum(1 for row in log if row.get("is_profane"))
    total_words = len(log)
    flagged = [row for row in log if row.get("is_profane")]
    return {
        "word_count": total_words,
        "profane_word_count": profanity_count,
        "flagged_count": len(flagged),
    }


def create_media_summary_html(log: Sequence[Dict[str, Any]], censor_path: str, options: Dict[str, Any], log_path: Optional[str], transcript_paths: Dict[str, str]) -> str:
    summary = media_log_summary(log)
    transcript_names = ", ".join(os.path.basename(path) for path in transcript_paths.values()) or "No transcript exports selected"
    log_name = os.path.basename(log_path) if log_path else "Export disabled"
    return (
        "<h2>Analysis Complete</h2>"
        "<ul>"
        f"<li>Words analyzed: <b>{summary['word_count']}</b></li>"
        f"<li>Profane words detected: <b>{summary['profane_word_count']}</b></li>"
        "</ul>"
        f"<p>Censored media: <b>{html.escape(os.path.basename(censor_path))}</b></p>"
        f"<p>Transcript exports: <b>{html.escape(transcript_names)}</b></p>"
        f"<p>Word log: <b>{html.escape(log_name)}</b></p>"
    )


def _word_status_map(full_log: Sequence[Dict[str, Any]]) -> Dict[Tuple[int, int, str], Dict[str, Any]]:
    return {(int(row["start_ms"]), int(row["end_ms"]), str(row["word"])): row for row in full_log}


def generate_transcript_txt(transcription: Dict[str, Any], log: Sequence[Dict[str, Any]], file_path: str, clean: bool) -> str:
    base, _ = os.path.splitext(file_path)
    path = f"{base}_{'conversation_CLEAN' if clean else 'conversation_RAW'}.txt"
    status = _word_status_map(log)
    lines: List[str] = []
    for segment in transcription.get("segments", []):
        words: List[str] = []
        for word_info in segment.get("words", []):
            if not isinstance(word_info, dict) or "word" not in word_info:
                continue
            word = word_info["word"].strip()
            key = (int(word_info["start"] * 1000), int(word_info["end"] * 1000), word)
            row = status.get(key, {})
            censor = clean and row.get("is_profane")
            words.append(MEDIA_TRANSCRIPT_REPLACEMENT if censor else word)
        if words:
            lines.append(" ".join(words).strip())
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return path


def generate_transcript_srt(transcription: Dict[str, Any], log: Sequence[Dict[str, Any]], file_path: str, clean: bool) -> str:
    base, _ = os.path.splitext(file_path)
    path = f"{base}_{'transcript_CLEAN' if clean else 'transcript_RAW'}.srt"
    status = _word_status_map(log)
    chunks: List[str] = []
    index = 1
    for segment in transcription.get("segments", []):
        words: List[str] = []
        for word_info in segment.get("words", []):
            if not isinstance(word_info, dict) or "word" not in word_info:
                continue
            word = word_info["word"].strip()
            key = (int(word_info["start"] * 1000), int(word_info["end"] * 1000), word)
            row = status.get(key, {})
            censor = clean and row.get("is_profane")
            words.append(MEDIA_TRANSCRIPT_REPLACEMENT if censor else word)
        text = " ".join(words).strip()
        if text:
            start_ms = int(segment.get("start", 0.0) * 1000)
            end_ms = int(segment.get("end", 0.0) * 1000)
            chunks.extend([str(index), f"{format_time_srt(start_ms)} --> {format_time_srt(end_ms)}", f"{text}\n"])
            index += 1
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(chunks))
    return path


def _fallback_output_copy(input_path: str) -> str:
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_CENSORED{ext}"
    if not os.path.exists(output_path):
        shutil.copyfile(input_path, output_path)
    return output_path


class DummyCallback:
    def emit(self, msg: Any) -> None:
        pass


@st.cache_resource(max_entries=1, show_spinner=False)
def _cached_load_asr(model_name: str) -> Any:
    b = require_backend()
    return b.load_ml_resources(DummyCallback(), False, model_name)


def process_media_file(file_path: str, options: Dict[str, Any], progress_callback: Any = None, progress_value_callback: Any = None) -> Dict[str, Any]:
    b = require_backend()
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    start_time = time.time()
    temp_files: List[str] = []

    rating_preset = options.get("rating_preset", "Default")
    preset_whitelist = get_rating_preset_whitelist(rating_preset)
    user_whitelist = b.load_word_list_from_text(options.get("whitelist_text", ""))
    b.GLOBAL_WHITELIST_WORDS = user_whitelist | preset_whitelist
    b.GLOBAL_BLACKLIST_WORDS = b.load_word_list_from_text(options.get("blacklist_text", ""))
    if preset_whitelist:
        emit(progress_callback, f"Rating preset [{rating_preset}] applied ({len(preset_whitelist)} whitelisted words).")
    emit(progress_callback, f"Loaded {len(b.GLOBAL_WHITELIST_WORDS)} total whitelist word(s).")
    emit(progress_callback, f"Loaded {len(b.GLOBAL_BLACKLIST_WORDS)} blacklist word(s).")

    asr_model = options.get("asr_model", "base.en")
    emit(progress_callback, f"Initializing ASR model ({asr_model})...")
    cached_model = _cached_load_asr(asr_model)
    if cached_model is not None:
        b.ML_MODEL_CACHE[asr_model] = cached_model
        b.ASR_MODEL_KEY_CURRENT = asr_model
    else:
        b.load_ml_resources(progress_callback, False, asr_model)

    emit(progress_value_callback, 5)
    pre_converted = b.pre_convert_to_wav(file_path, progress_callback)
    if pre_converted != file_path:
        temp_files.append(pre_converted)

    emit(progress_value_callback, 10)
    vad_path = b.apply_vad_filtering(pre_converted, progress_callback)
    if vad_path != pre_converted:
        temp_files.append(vad_path)

    emit(progress_value_callback, 15)
    transcription = b.transcribe_audio(vad_path, progress_callback)
    emit(progress_callback, "Generating word-level log and transcript exports.")
    log = b.generate_conversation_log(transcription, 0.0, False)

    base, _ = os.path.splitext(file_path)
    log_path = None
    if options.get("export_json_log", True):
        log_path = f"{base}_log.json"
        with open(log_path, "w", encoding="utf-8") as handle:
            json.dump(log, handle, indent=4)

    transcript_paths: Dict[str, str] = {}
    if options.get("export_raw_txt"):
        transcript_paths["raw_txt"] = generate_transcript_txt(transcription, log, file_path, False)
    if options.get("export_raw_srt"):
        transcript_paths["raw_srt"] = generate_transcript_srt(transcription, log, file_path, False)
    if options.get("export_clean_txt"):
        transcript_paths["clean_txt"] = generate_transcript_txt(transcription, log, file_path, True)
    if options.get("export_clean_srt"):
        transcript_paths["clean_srt"] = generate_transcript_srt(transcription, log, file_path, True)

    emit(progress_value_callback, 50)
    censor_path = b.censor_media(
        file_path,
        base,
        log,
        options.get("mode", "sound"),
        False,
        options.get("sound", "B"),
        options.get("custom_sound_path", ""),
        options.get("censor_volume", 0.0),
        progress_callback,
        progress_value_callback,
        overlap_censor=bool(options.get("overlap_censor", False)),
        marked_audio_volume=float(options.get("marked_audio_volume", 100.0)),
        padding_before_ms=int(options.get("padding_before_ms", 50)),
        padding_after_ms=int(options.get("padding_after_ms", 50)),
        custom_sound_paths=options.get("custom_sound_paths", []),
        loop_censor_sound=bool(options.get("loop_censor_sound", True)),
    )
    if not os.path.exists(censor_path):
        censor_path = _fallback_output_copy(file_path)

    for temp_path in temp_files:
        if os.path.exists(temp_path) and temp_path != file_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    elapsed = time.time() - start_time
    emit(progress_callback, f"Processing finished in {elapsed:.2f} seconds.")
    return {
        "summary_html": create_media_summary_html(log, censor_path, options, log_path, transcript_paths),
        "summary": media_log_summary(log),
        "censored_path": censor_path,
        "log_path": log_path,
        "transcript_paths": transcript_paths,
        "log": log,
        "transcription": transcription,
        "elapsed_seconds": round(elapsed, 2),
    }
