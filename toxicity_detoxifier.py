import os
import re
import string
import numpy as np
try:
    import streamlit as st
except ImportError:
    st = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    lemmatizer = WordNetLemmatizer()
    custom_stopwords = set(stopwords.words('english')) - {'not', 'no', 'nor', 'against', 'you', 'your', 'me'}
except Exception:
    lemmatizer = None
    custom_stopwords = set()

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    try:
        from kaggle_secrets import UserSecretsClient
        GROQ_API_KEY = UserSecretsClient().get_secret("GROQ_API_KEY")
    except Exception:
        pass

client = Groq(api_key=GROQ_API_KEY) if Groq and GROQ_API_KEY else None

def advanced_clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'https?://\S+|www\.\S+|<.*?>+', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\d+', '', text)
    if lemmatizer:
        words = [lemmatizer.lemmatize(w) for w in text.split() if w not in custom_stopwords]
    else:
        words = [w for w in text.split() if w not in custom_stopwords]
    return " ".join(words)


CATEGORIES = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, "toxicity_detection_model.keras")

MODEL_LOAD_ERROR = None
model = None

def _load_keras_file(target_path):
    import tensorflow as tf
    import zipfile
    import json
    import tempfile
    import shutil

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
            target_path, custom_objects=custom_objs, compile=False, safe_mode=False
        )
    except Exception:
        pass

    if zipfile.is_zipfile(target_path):
        temp_dir = tempfile.mkdtemp()
        try:
            sanitized_path = os.path.join(temp_dir, "sanitized_model.keras")
            with zipfile.ZipFile(target_path, 'r') as zin:
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
                shutil.copyfile(sanitized_path, target_path)
            except Exception:
                pass
            return loaded_model
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return tf.keras.models.load_model(
        target_path, custom_objects=custom_objs, compile=False, safe_mode=False
    )

def _get_model():
    global MODEL_LOAD_ERROR

    try:
        import tensorflow as tf
    except ImportError:
        MODEL_LOAD_ERROR = "TensorFlow is not installed."
        return None

    try:
        if not os.path.exists(MODEL_PATH):
            MODEL_LOAD_ERROR = f"Model file not found at: {MODEL_PATH}"
            return None

        return _load_keras_file(MODEL_PATH)

    except Exception as e:
        MODEL_LOAD_ERROR = str(e)
        return None


if st is not None:
    @st.cache_resource
    def load_cached_detox_model():
        return _get_model()

    get_model = load_cached_detox_model
else:
    _loaded_model = None

    def get_model():
        global _loaded_model

        if _loaded_model is None:
            _loaded_model = _get_model()

        return _loaded_model

    
DETOX_SYSTEM_PROMPT = """
You are a direct text rephraser.
Transform rude or toxic comments into polite, constructive alternatives while preserving the intent.

CRITICAL INSTRUCTIONS:
- Do NOT output your thought process, analysis, drafts, or reasoning steps.
- Output strictly the final polite sentence ONLY.
- No introductory phrases, no explanations, no quotes.
"""


def end_to_end_detoxifier(raw_text: str, threshold: float = 0.60) -> dict:

    if not raw_text or not raw_text.strip():
        return {
            "original_text": raw_text,
            "detoxified_text": raw_text,
            "was_modified": False,
            "top_category": "NONE",
            "toxicity_score": 0.0,
            "category_scores": {cat: 0.0 for cat in CATEGORIES}
        }

    cleaned_input = advanced_clean_text(raw_text)
    import tensorflow as tf
    input_array = tf.constant([cleaned_input])

    model = get_model()
    if model is not None:
        probabilities = model.predict(input_array, verbose=0)[0]
        max_score = float(np.max(probabilities))
        top_category = CATEGORIES[np.argmax(probabilities)].upper()
        category_scores = {
            cat: float(prob) for cat, prob in zip(CATEGORIES, probabilities)
        }

    else:
        max_score = 0.0
        top_category = "UNKNOWN"
        category_scores = {}

    if max_score < threshold:
        return {
            "original_text": raw_text,
            "detoxified_text": raw_text,
            "was_modified": False,
            "top_category": top_category,
            "toxicity_score": max_score,
            "category_scores": category_scores
        }

    response = client.chat.completions.create(
        model="allam-2-7b",
        messages=[
            {"role": "system", "content": DETOX_SYSTEM_PROMPT},
            {"role": "user", "content": f"Rewrite this comment politely: {raw_text}"}
        ],
        temperature=0.1,
        max_tokens=600
    )

    raw_content = response.choices[0].message.content

    if "</think>" in raw_content:
        clean_content = raw_content.split("</think>")[-1].strip()
    else:
        clean_content = re.sub(r'<think>.*', '', raw_content, flags=re.DOTALL).strip()
        if not clean_content:
            clean_content = raw_content.split("\n")[-1].strip()

    return {
        "original_text": raw_text,
        "detoxified_text": clean_content,
        "was_modified": True,
        "top_category": top_category,
        "toxicity_score": max_score,
        "category_scores": category_scores
    }