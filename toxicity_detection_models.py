import locale
import io
import os
import sys
import joblib
import numpy as np
import tensorflow as tf
import whisper
from unittest.mock import patch

locale.getpreferredencoding = lambda do_setlocale=True: "utf-8"
os.environ["PYTHONUTF8"] = "1"

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

with patch("whisper.tqdm"):
    speech_model = whisper.load_model("base")

# مسار المجلد اللي فيه الملف ده نفسه (بيشتغل صح مهما كان مكان تشغيل السكريبت)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "toxicity_detection_model.keras")
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.pkl")


@tf.keras.utils.register_keras_serializable()
def weighted_binary_crossentropy(y_true, y_pred):
    return tf.keras.losses.binary_crossentropy(y_true, y_pred)


if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Toxicity model not found at: {MODEL_PATH}\n"
        f"Make sure 'toxicity_detection_model.keras' is placed next to this script."
    )

toxicity_model = tf.keras.models.load_model(
    MODEL_PATH,
    custom_objects={
        "weighted_binary_crossentropy": weighted_binary_crossentropy
    },
    compile=False,
)

if not os.path.exists(CATEGORIES_PATH):
    raise FileNotFoundError(
        f"categories.pkl not found at: {CATEGORIES_PATH}\n"
        f"Make sure 'categories.pkl' is placed next to this script."
    )

categories = joblib.load(CATEGORIES_PATH)


def transcribe_media(media_path):
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

    input_text = np.array([text], dtype=object)
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