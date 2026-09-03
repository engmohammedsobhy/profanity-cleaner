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
MODEL_PATH = os.path.join(BASE_DIR, "toxicity_detection_model.keras")
if not os.path.exists(MODEL_PATH):
    alt_model_path = os.path.join(BASE_DIR, "toxicity_model.keras")
    if os.path.exists(alt_model_path):
        MODEL_PATH = alt_model_path

CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.pkl")

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

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Toxicity model not found at: {MODEL_PATH}\n"
            f"Make sure 'toxicity_detection_model.keras' is placed in project root."
        )

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
            MODEL_PATH,
            custom_objects=custom_objs,
            compile=False,
            safe_mode=False,
        )
    except Exception:
        pass

    if zipfile.is_zipfile(MODEL_PATH):
        temp_dir = tempfile.mkdtemp()
        try:
            sanitized_path = os.path.join(temp_dir, "sanitized_model.keras")
            with zipfile.ZipFile(MODEL_PATH, 'r') as zin:
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
                shutil.copyfile(sanitized_path, MODEL_PATH)
            except Exception:
                pass
            return loaded_model
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return tf.keras.models.load_model(
        MODEL_PATH,
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
        return _load_toxicity_model()

    @st.cache_resource
    def get_categories():
        return _load_categories()
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