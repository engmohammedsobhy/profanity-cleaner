import os
import re
import string
import json
import zipfile
import tempfile
import shutil
import numpy as np

os.environ["TF_USE_LEGACY_KERAS"] = "1"

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

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

ENGLISH_CATEGORIES = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
EN_MODEL_PATH = os.path.join(CURRENT_DIR, "toxicity_detection_model.keras")

ARABIC_CATEGORIES = ['toxic']
ARABIC_DEFAULT_THRESHOLD = 0.50
ENGLISH_DEFAULT_THRESHOLD = 0.40

POSSIBLE_AR_NAMES = [
    "arabic_sentiment.keras.zip",
    "arabic_sentiment.keras",
    "arabic_model.keras",
    "arabic_toxicity_model.keras",
    "model.weights.h5"
]

MODEL_LOAD_ERROR = None
ARABIC_MODEL_LOAD_ERROR = None

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

def clean_arabic_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'https?://\S+|www\.\S+|@\w+', '', text)
    text = re.sub(r'[\u0617-\u061A\u064B-\u0652\u0640]', '', text)
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ؤ", "و", text)
    text = re.sub(r"ئ", "ي", text)
    text = text.replace("#", "")
    text = re.sub(r'[^\u0600-\u06FF\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def _load_keras_file(target_path):
    import tensorflow as tf

    try:
        @tf.keras.utils.register_keras_serializable()
        def weighted_binary_crossentropy(y_true, y_pred):
            return tf.keras.losses.binary_crossentropy(y_true, y_pred)
        custom_objs = {"weighted_binary_crossentropy": weighted_binary_crossentropy}
    except Exception:
        custom_objs = {}

    try:
        return tf.keras.models.load_model(target_path, custom_objects=custom_objs, compile=False)
    except Exception as e:
        if zipfile.is_zipfile(target_path):
            try:
                temp_dir = tempfile.mkdtemp()
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
                loaded_model = tf.keras.models.load_model(sanitized_path, custom_objects=custom_objs, compile=False)
                try:
                    shutil.copyfile(sanitized_path, target_path)
                except Exception:
                    pass
                shutil.rmtree(temp_dir, ignore_errors=True)
                return loaded_model
            except Exception:
                pass
        raise e

def _get_english_model():
    global MODEL_LOAD_ERROR
    try:
        import tensorflow as tf
    except ImportError:
        MODEL_LOAD_ERROR = "TensorFlow is not installed."
        return None

    try:
        if not os.path.exists(EN_MODEL_PATH):
            MODEL_LOAD_ERROR = f"Model file not found at: {EN_MODEL_PATH}"
            return None
        return _load_keras_file(EN_MODEL_PATH)
    except Exception as e:
        MODEL_LOAD_ERROR = str(e)
        return None

def _resolve_arabic_model_path():
    for name in POSSIBLE_AR_NAMES:
        candidate = os.path.join(CURRENT_DIR, name)
        if os.path.exists(candidate):
            return candidate
        working_candidate = os.path.join(os.getcwd(), name)
        if os.path.exists(working_candidate):
            return working_candidate
    return None

def _get_arabic_model():
    global ARABIC_MODEL_LOAD_ERROR
    try:
        import tensorflow as tf
    except ImportError:
        ARABIC_MODEL_LOAD_ERROR = "TensorFlow is not installed."
        return None

    model_path = _resolve_arabic_model_path()
    if not model_path:
        ARABIC_MODEL_LOAD_ERROR = f"Arabic model file not found. Searched for: {POSSIBLE_AR_NAMES}"
        return None

    try:
        return _load_keras_file(model_path)
    except Exception as e:
        ARABIC_MODEL_LOAD_ERROR = str(e)
        return None

if st is not None:
    @st.cache_resource
    def load_cached_en_model():
        return _get_english_model()

    @st.cache_resource
    def load_cached_ar_model():
        return _get_arabic_model()

    get_english_model = load_cached_en_model
    get_arabic_model = load_cached_ar_model
else:
    _en_model = None
    _ar_model = None

    def get_english_model():
        global _en_model
        if _en_model is None:
            _en_model = _get_english_model()
        return _en_model

    def get_arabic_model():
        global _ar_model
        if _ar_model is None:
            _ar_model = _get_arabic_model()
        return _ar_model

DETOX_SYSTEM_PROMPT_EN = """
You are a direct text rephraser.
Transform rude or toxic comments into polite, constructive alternatives while preserving the intent.

CRITICAL INSTRUCTIONS:
- Do NOT output your thought process, analysis, drafts, or reasoning steps.
- Output strictly the final polite sentence ONLY.
- No introductory phrases, no explanations, no quotes.
"""

DETOX_SYSTEM_PROMPT_AR = """
You are a text detoxification engine.
Your task is to REPHRASE the user's input sentence to express the exact same meaning, criticism, or opinion, but using professional, respectful, and civilized language.

STRICT RULES:
1. Maintain the ORIGINAL speaker's perspective and grammatical pronouns (If the user addresses someone with 'You', your output MUST still address them with 'You').
2. Do NOT reply to the user.
3. Do NOT defend the person being spoken to.
4. Do NOT say 'I think', 'You shouldn't say', or give advice.
5. Output ONLY the rephrased sentence in Arabic with zero explanation, zero quotes, and zero introductory words.
"""

def end_to_end_detoxifier(raw_text: str, threshold: float = None, language: str = "English") -> dict:
    categories = ARABIC_CATEGORIES if language == "Arabic" else ENGLISH_CATEGORIES

    if threshold is None:
        threshold = ARABIC_DEFAULT_THRESHOLD if language == "Arabic" else ENGLISH_DEFAULT_THRESHOLD

    if not raw_text or not raw_text.strip():
        return {
            "original_text": raw_text,
            "detoxified_text": raw_text,
            "was_modified": False,
            "top_category": "NONE",
            "toxicity_score": 0.0,
            "category_scores": {cat: 0.0 for cat in categories}
        }

    import tensorflow as tf

    if language == "Arabic":
        cleaned_input = clean_arabic_text(raw_text)
        input_array = tf.constant([cleaned_input], dtype=tf.string)
        model = get_arabic_model()

        if model is not None:
            raw_pred = model.predict(input_array, verbose=0)
            positive_probability = float(np.squeeze(raw_pred))
            toxicity_score = 1.0 - positive_probability
            max_score = float(np.clip(toxicity_score, 0.0, 1.0))
            top_category = "TOXIC" if max_score >= threshold else "SAFE"
            category_scores = {"toxic": max_score}
        else:
            max_score = 0.0
            top_category = "UNKNOWN"
            category_scores = {}
    else:
        cleaned_input = advanced_clean_text(raw_text)
        input_array = tf.constant([cleaned_input])
        model = get_english_model()

        if model is not None:
            probabilities = model.predict(input_array, verbose=0)[0]
            max_score = float(np.max(probabilities))
            top_category = ENGLISH_CATEGORIES[np.argmax(probabilities)].upper()
            category_scores = {
                cat: float(prob) for cat, prob in zip(ENGLISH_CATEGORIES, probabilities)
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

    if not client:
        return {
            "original_text": raw_text,
            "detoxified_text": raw_text,
            "was_modified": False,
            "top_category": top_category,
            "toxicity_score": max_score,
            "category_scores": category_scores
        }

    system_prompt = DETOX_SYSTEM_PROMPT_AR if language == "Arabic" else DETOX_SYSTEM_PROMPT_EN
    user_prompt = (
        f"Rephrase this exact criticism politely while keeping the same subject and perspective: {raw_text}"
        if language == "Arabic"
        else f"Rewrite this comment politely: {raw_text}"
    )

    try:
        response = client.chat.completions.create(
            model="allam-2-7b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=500
        )

        raw_content = response.choices[0].message.content

        
        if "</think>" in raw_content:
            clean_content = raw_content.split("</think>")[-1].strip()
        else:
            clean_content = re.sub(r'<think>.*', '', raw_content, flags=re.DOTALL).strip()
            if not clean_content:
                clean_content = raw_content.split("\n")[-1].strip()
    except Exception:
        clean_content = raw_text

    return {
        "original_text": raw_text,
        "detoxified_text": clean_content,
        "was_modified": True,
        "top_category": top_category,
        "toxicity_score": max_score,
        "category_scores": category_scores
    }