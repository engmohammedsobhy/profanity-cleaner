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
os.environ["TF_USE_LEGACY_KERAS"] = "1"

try:
    import importlib
    for mod_path in [
        'tf_keras.src.layers.preprocessing.index_lookup',
        'keras.layers.preprocessing.index_lookup',
        'keras.src.layers.preprocessing.index_lookup',
        'tensorflow.python.keras.layers.preprocessing.index_lookup',
    ]:
        try:
            mod = importlib.import_module(mod_path)
            for cls_name in ['IndexLookup', 'StringLookup', 'IntegerLookup']:
                if hasattr(mod, cls_name):
                    cls_obj = getattr(mod, cls_name)
                    if hasattr(cls_obj, 'load_assets'):
                        orig_func = getattr(cls_obj, 'load_assets')
                        def _make_safe(orig):
                            def _safe_load_assets(self, dir_path):
                                if dir_path is None:
                                    return
                                try:
                                    return orig(self, dir_path)
                                except Exception:
                                    pass
                            return _safe_load_assets
                        setattr(cls_obj, 'load_assets', _make_safe(orig_func))
        except Exception:
            pass
except Exception:
    pass

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


def _sanitize_config_for_keras2(obj, is_input_layer=False, current_class=None):
    if isinstance(obj, dict):
        class_name = obj.get('class_name', current_class or '')
        is_input = (class_name == 'InputLayer') or is_input_layer
        res = {}
        for k, v in obj.items():
            if k in ('build_config', 'registered_name', 'shared_object_id', 'quantization_config', 'optional', 'zero_output_for_mask', 'vocabulary_size', 'encoding'):
                continue
            if k == 'batch_shape':
                if is_input:
                    res['batch_input_shape'] = _sanitize_config_for_keras2(v, is_input, class_name)
                continue
            elif k == 'dtype':
                if class_name == 'TextVectorization':
                    res[k] = 'string'
                elif isinstance(v, dict):
                    res[k] = 'float32'
                else:
                    res[k] = v
            elif k == 'class_name' and v == 'function':
                res[k] = 'weighted_binary_crossentropy'
            elif k == 'module' and v == 'builtins':
                res[k] = 'keras.losses'
            else:
                res[k] = _sanitize_config_for_keras2(v, is_input, class_name)
        return res
    elif isinstance(obj, list):
        return [_sanitize_config_for_keras2(item, is_input_layer, current_class) for item in obj]
    return obj


def _load_toxicity_model():
    import tensorflow as tf
    try:
        import tf_keras as keras
    except ImportError:
        import tensorflow.keras as keras

    class FixedTextVectorization(keras.layers.TextVectorization):
        @classmethod
        def from_config(cls, config):
            cfg = dict(config)
            if cfg.get("dtype") != "string":
                cfg["dtype"] = "string"
            return super().from_config(cfg)

        def load_assets(self, dir_path):
            if dir_path is None:
                return
            try:
                return super().load_assets(dir_path)
            except Exception:
                pass

    import zipfile
    import json
    import tempfile
    import shutil

    model_path = _ensure_model_path()

    def weighted_binary_crossentropy(y_true, y_pred):
        return tf.keras.losses.binary_crossentropy(y_true, y_pred)

    try:
        @keras.utils.register_keras_serializable(package="builtins", name="function")
        def reg_func1(y_true, y_pred):
            return tf.keras.losses.binary_crossentropy(y_true, y_pred)

        @keras.utils.register_keras_serializable(name="function")
        def reg_func2(y_true, y_pred):
            return tf.keras.losses.binary_crossentropy(y_true, y_pred)
    except Exception:
        pass

    custom_objs = {
        "function": weighted_binary_crossentropy,
        "builtins.function": weighted_binary_crossentropy,
        "weighted_binary_crossentropy": weighted_binary_crossentropy,
        "builtins.weighted_binary_crossentropy": weighted_binary_crossentropy,
        "loss": weighted_binary_crossentropy,
        "loss_function": weighted_binary_crossentropy,
        "TextVectorization": FixedTextVectorization,
        "keras.layers.TextVectorization": FixedTextVectorization,
    }

    def _finalize_model(m):
        if m is None:
            return m
        try:
            for layer in m.layers:
                if hasattr(layer, 'get_vocabulary') or 'vector' in getattr(layer, 'name', '').lower():
                    try:
                        vocab = layer.get_vocabulary()
                        if vocab and len(vocab) > 0:
                            layer.set_vocabulary(vocab)
                    except Exception as err:
                        print(f"Failed to re-initialize vectorizer vocabulary: {err}")
        except Exception:
            pass
        return m

    try:
        return _finalize_model(keras.models.load_model(model_path, custom_objects=custom_objs, compile=False))
    except Exception:
        pass

    try:
        return _finalize_model(tf.keras.models.load_model(model_path, custom_objects=custom_objs, compile=False))
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
                            try:
                                cfg = json.loads(data.decode('utf-8'))
                                cfg['compile_config'] = None
                                clean_cfg = _sanitize_config_for_keras2(cfg)
                                data = json.dumps(clean_cfg).encode('utf-8')
                            except Exception:
                                pass
                        zout.writestr(item, data)

            sanitized_err = None
            try:
                loaded_model = keras.models.load_model(sanitized_path, custom_objects=custom_objs, compile=False)
                try:
                    shutil.copyfile(sanitized_path, model_path)
                except Exception:
                    pass
                return _finalize_model(loaded_model)
            except Exception as exc:
                sanitized_err = exc

            try:
                loaded_model = tf.keras.models.load_model(sanitized_path, custom_objects=custom_objs, compile=False)
                try:
                    shutil.copyfile(sanitized_path, model_path)
                except Exception:
                    pass
                return _finalize_model(loaded_model)
            except Exception as exc:
                sanitized_err = exc

            if sanitized_err:
                print(f"[Model Loader] Sanitized model load failed: {sanitized_err}")
                raise sanitized_err
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    try:
        return _finalize_model(keras.models.load_model(model_path, custom_objects=custom_objs, compile=False))
    except Exception:
        return _finalize_model(tf.keras.models.load_model(model_path, custom_objects=custom_objs, compile=False))


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
        try:
            m = _load_toxicity_model()
            if m is None:
                raise RuntimeError("Toxicity model loading returned None")
            return m
        except Exception as e:
            if st is not None:
                st.error(f"Unredacted Model Load Error: {e}")
            raise e

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


_VOCAB_MAP = None

def _get_vocab_map():
    global _VOCAB_MAP
    if _VOCAB_MAP is not None:
        return _VOCAB_MAP
    vocab_path = os.path.join(BASE_DIR, "vocab.json")
    if os.path.exists(vocab_path):
        try:
            import json
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocab_list = json.load(f)
                _VOCAB_MAP = {w: i for i, w in enumerate(vocab_list)}
                return _VOCAB_MAP
        except Exception:
            pass
    return {}


def text_to_sequence(text, max_len=150):
    vocab_map = _get_vocab_map()
    import re
    clean_text = re.sub(r'[^\w\s]', '', str(text).lower())
    words = clean_text.split()
    seq = [vocab_map.get(w, 1) for w in words[:max_len]]
    if len(seq) < max_len:
        seq += [0] * (max_len - len(seq))
    return np.array([seq], dtype=np.int32)


def predict_toxicity_probabilities(model, text):
    vocab_map = _get_vocab_map()
    if vocab_map:
        try:
            seq = text_to_sequence(text)
            if hasattr(model, "layers") and len(model.layers) > 1 and ("vector" in getattr(model.layers[0], "name", "").lower() or hasattr(model.layers[0], "get_vocabulary")):
                import tensorflow as tf
                sub_model = tf.keras.Sequential(model.layers[1:])
                return sub_model(seq, training=False).numpy()[0]
            else:
                return model(seq, training=False).numpy()[0]
        except Exception as e:
            print(f"[Predict Fallback] Decoupled vectorizer evaluation failed: {e}")

    import tensorflow as tf
    input_text = tf.constant([str(text)])
    try:
        return model(input_text, training=False).numpy()[0]
    except Exception:
        return model.predict(input_text, verbose=0)[0]


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

    probabilities = predict_toxicity_probabilities(toxicity_model, text)

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