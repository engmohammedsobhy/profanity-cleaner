import os
import re
import string
import numpy as np
try:
    import tensorflow as tf
except ImportError:
    tf = None

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
    words = [lemmatizer.lemmatize(w) for w in text.split() if w not in custom_stopwords]
    return " ".join(words)

CATEGORIES = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, "toxicity_model.keras")

try:
    model = tf.keras.models.load_model(MODEL_PATH) if tf is not None else None
except Exception as e:
    model = None
    print(f"Warning: Could not load toxicity model from {MODEL_PATH}: {e}")

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
    input_array = np.array([cleaned_input], dtype=object)

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