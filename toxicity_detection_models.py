import locale
import io
import os
import sys
import joblib
import numpy as np

try:
    import streamlit as st
except ImportError:
    st = None

locale.getpreferredencoding = lambda do_setlocale=True: "utf-8"
os.environ["PYTHONUTF8"] = "1"

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_URL = "https://github.com/engmohammedsobhy/profanity-cleaner/releases/download/v1.0.0/toxicity_model.keras"
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.pkl")

def _ensure_model_path():
    import zipfile
    import urllib.request
    import tempfile
    import shutil

    primary_path = os.path.join(BASE_DIR, "toxicity_detection_model.keras")
    alt_path = os.path.join(BASE_DIR, "toxicity_model.keras")
    tmp_path = os.path.join(tempfile.gettempdir(), "toxicity_model.keras")

    for path in (primary_path, alt_path, tmp_path):
        if os.path.exists(path):
            try:
                if os.path.getsize(path) > 1_000_000 and zipfile.is_zipfile(path):
                    return path
            except Exception:
                pass

    def _download(url, dest):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)

    try:
        if os.path.exists(primary_path) and os.path.getsize(primary_path) <= 1_000_000:
            os.remove(primary_path)
    except Exception:
        pass

    try:
        _download(MODEL_URL, primary_path)
        if os.path.exists(primary_path) and os.path.getsize(primary_path) > 1_000_000 and zipfile.is_zipfile(primary_path):
            return primary_path
    except Exception:
        pass

    try:
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) <= 1_000_000:
            os.remove(tmp_path)
    except Exception:
        pass

    try:
        _download(MODEL_URL, tmp_path)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1_000_000 and zipfile.is_zipfile(tmp_path):
            return tmp_path
    except Exception as e:
        raise FileNotFoundError(f"Failed to download model to {tmp_path}: {e}")

    raise FileNotFoundError("Could not acquire a valid toxicity model file.")


def _load_speech_model():
    import whisper
    from unittest.mock import patch
    with patch("whisper.tqdm"):
        return whisper.load_model("base")


def _load_toxicity_model():
    import tensorflow as tf
    import zipfile
    import json
    import tempfile
    import shutil

    model_path = _ensure_model_path()

    def weighted_binary_crossentropy(y_true, y_pred):
        return tf.keras.losses.binary_crossentropy(y_true, y_pred)

    try:
        @tf.keras.utils.register_keras_serializable(name="function")
        def reg_func(y_true, y_pred):
            return tf.keras.losses.binary_crossentropy(y_true, y_pred)
    except Exception:
        pass

    custom_objs = {
        "function": weighted_binary_crossentropy,
        "weighted_binary_crossentropy": weighted_binary_crossentropy,
    }

    try:
        return tf.keras.models.load_model(
            model_path,
            custom_objects=custom_objs,
            compile=False,
            safe_mode=False,
        )
    except Exception:
        pass

    if zipfile.is_zipfile(model_path):
        temp_dir = tempfile.mkdtemp()
        try:
            sanitized_path = os.path.join(temp_dir, "sanitized_model.keras")
            with zipfile.ZipFile(model_path, 'r') as zin:
                with zipfile.ZipFile(sanitized_path, 'w') as zout:
                    for item in zin.infolist():
                        data = zin.read(item.filename)
                        if item.filename == 'config.json':
                            cfg = json.loads(data.decode('utf-8'))
                            cfg['compile_config'] = None
                            data = json.dumps(cfg).encode('utf-8')
                        zout.writestr(item, data)
            loaded_model = tf.keras.models.load_model(
                sanitized_path, custom_objects=custom_objs, compile=False, safe_mode=False
            )
            try:
                shutil.copyfile(sanitized_path, model_path)
            except Exception:
                pass
            return loaded_model
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return tf.keras.models.load_model(
        model_path,
        custom_objects=custom_objs,
        compile=False,
        safe_mode=False,
    )


def _load_categories():
    if not os.path.exists(CATEGORIES_PATH):
        return ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
    return joblib.load(CATEGORIES_PATH)


if st is not None:
    @st.cache_resource
    def get_speech_model():
        return _load_speech_model()

    @st.cache_resource
    def get_toxicity_model():
        m = _load_toxicity_model()
        if m is None:
            raise RuntimeError("Toxicity model loading returned None")
        return m

    @st.cache_resource
    def get_categories():
        return _load_categories()

    load_speech_model = get_speech_model
    load_toxicity_model = get_toxicity_model
else:
    _speech_m = None
    _tox_m = None
    _cats = None

    def get_speech_model():
        global _speech_m
        if _speech_m is None:
            _speech_m = _load_speech_model()
        return _speech_m

    def get_toxicity_model():
        global _tox_m
        if _tox_m is None:
            _tox_m = _load_toxicity_model()
        return _tox_m

    def get_categories():
        global _cats
        if _cats is None:
            _cats = _load_categories()
        return _cats

    load_speech_model = get_speech_model
    load_toxicity_model = get_toxicity_model


def transcribe_media(media_path):
    speech_model = get_speech_model()
    result = speech_model.transcribe(media_path)
    return result["text"].strip()


def analyze_text_toxicity(text, threshold=0.70):
    if not text:
        return {
            "text": "",
            "probabilities": {},
            "violations": [],
            "is_safe": True,
        }

    toxicity_model = get_toxicity_model()
    categories = get_categories()

    import tensorflow as tf
    input_text = tf.constant([text])
    probabilities = toxicity_model.predict(input_text, verbose=0)[0]

    class_probs = {
        cat.upper(): float(prob * 100)
        for cat, prob in zip(categories, probabilities)
    }

    violations = [
        {"category": cat.upper(), "score": float(prob * 100)}
        for cat, prob in zip(categories, probabilities)
        if prob >= threshold
    ]

    return {
        "text": text,
        "probabilities": class_probs,
        "violations": violations,
        "is_safe": len(violations) == 0,
    }


def analyze_media_toxicity(media_path, threshold=0.70):
    extracted_text = transcribe_media(media_path)
    return analyze_text_toxicity(extracted_text, threshold=threshold)