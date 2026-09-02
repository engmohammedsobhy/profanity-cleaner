import locale
locale.getpreferredencoding = lambda do_setlocale=True: "utf-8"
import io
import os
import sys
import joblib
import numpy as np
import tensorflow as tf
import whisper

# 1. إجبار نظام Windows على قراءة النصوص بترميز UTF-8 لتفادي خطأ charmap codec
os.environ["PYTHONUTF8"] = "1"
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 2. تحميل موديل Whisper
speech_model = whisper.load_model("base")


# 3. دالة الـ Loss المخصصة
@tf.keras.utils.register_keras_serializable()
def weighted_binary_crossentropy(y_true, y_pred):
    return tf.keras.losses.binary_crossentropy(y_true, y_pred)


# 4. تحميل الموديل بحماية UTF-8 وبدون Compilation
try:
    toxicity_model = tf.keras.models.load_model(
        "toxicity_detection_model.keras",
        custom_objects={
            "weighted_binary_crossentropy": weighted_binary_crossentropy
        },
        compile=False,
    )
except Exception:
    toxicity_model = tf.keras.models.load_model(
        "toxicity_detection_model.keras", compile=False
    )

categories = joblib.load("categories.pkl")


# --- باقي الدوال المنفصلة كما هي ---


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