import torch
import torchaudio
import whisper
import sys
import os
import time
import random
import json
import re
import platform
from typing import List, Dict, Any, Tuple, Set, Callable
from urllib.parse import quote



try:
    import whisper
    from better_profanity import profanity
    from pydub import AudioSegment
    import numpy as np
    import docx
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torchaudio
    import soundfile as sf
except ImportError as e:
    print(f"INFO: Failed to import optional ML/Media libraries: {e}")


            
import ctypes
import platform

def set_app_user_model_id(app_id: str): #--------------------------------------------------------------------------------------------------------------------------------
    if platform.system() == 'Windows':
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except AttributeError:
            pass




DEFAULT_TOXICITY_THRESHOLD = 0.75
MIN_TOXICITY_WORD_COUNT = 3
MEDIA_TRANSCRIPT_REPLACEMENT = "****"
MIN_SEGMENT_DURATION_MS = 1000 # Kept for reference, but removed from SRT logic
SPLASH_FADE_DURATION_MS = 500
SPLASH_INITIAL_DELAY_MS = 1500

ASR_MODEL_CHOICE = "base.en"

# --- MODIFICATION: ML Model Caching ---
ML_MODEL_CACHE: Dict[str, Any] = {} # Cache for ASR models
ASR_MODEL_KEY_CURRENT: str = ASR_MODEL_CHOICE # Key for the currently active ASR model
# Removed global ASR_MODEL

CENSOR_SOUND_DIR = os.path.dirname(os.path.abspath(__file__))
DOLPHIN_SOUND_PATH = os.path.join(CENSOR_SOUND_DIR, "dolphin.wav")
QUACK_SOUND_PATH = os.path.join(CENSOR_SOUND_DIR, "quack.wav")
TRIGGERED_SOUND_PATH = os.path.join(CENSOR_SOUND_DIR, "triggered.wav")

MEDIA_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.mp3', '.wav', '.m4a')
TEXT_EXTENSIONS = ('.txt', '.docx')

PROFANITY_DICTIONARY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profanity_dictionary.json")

def load_profanity_dictionary_json() -> Dict[str, Any]:
    if os.path.exists(PROFANITY_DICTIONARY_FILE):
        try:
            with open(PROFANITY_DICTIONARY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load profanity dictionary JSON: {e}")
    return {}

PROFANITY_DICTIONARY = load_profanity_dictionary_json()

try:#---------------------------------------------------------------------------------------------------------------------------------------------------------------------
    profanity.load_censor_words()
except NameError:
    pass

TOXICITY_MODEL = None
TOXICITY_TOKENIZER = None
try:
    TOXICITY_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except NameError:
    TOXICITY_DEVICE = None

VAD_MODEL = None
VAD_SAMPLE_RATE = 16000

VAD_UTILS_REFERENCE = None

GLOBAL_WHITELIST_WORDS: Set[str] = set()
GLOBAL_BLACKLIST_WORDS: Set[str] = set()

ICON_COLOR_UNCHECKED = "#ffffff"
ICON_COLOR_CHECKED = "#000000"

SVG_BASE_DIR = CENSOR_SOUND_DIR

SVG_MAP_WHITE = {
    "silence": os.path.join(SVG_BASE_DIR, r"xw.svg"),
    "sound": os.path.join(SVG_BASE_DIR, r"xw2.svg"),
    "sine": os.path.join(SVG_BASE_DIR, r"xw3.svg"),
    "quack": os.path.join(SVG_BASE_DIR, r"xw4.svg"),
    "dolphin": os.path.join(SVG_BASE_DIR, r"xw5.svg"),
    "triggered": os.path.join(SVG_BASE_DIR, r"xw6.svg"),
}

SVG_MAP_BLACK = {
    "silence": os.path.join(SVG_BASE_DIR, r"xb.svg"),
    "sound": os.path.join(SVG_BASE_DIR, r"xb2.svg"),
    "sine": os.path.join(SVG_BASE_DIR, r"xb3.svg"),
    "quack": os.path.join(SVG_BASE_DIR, r"xb4.svg"),
    "dolphin": os.path.join(SVG_BASE_DIR, r"xb5.svg"),
    "triggered": os.path.join(SVG_BASE_DIR, r"xb6.svg"),
}

MASCOT_SVG_PATHS = {
    "media": os.path.join(CENSOR_SOUND_DIR, "m1.svg"),
    "text": os.path.join(CENSOR_SOUND_DIR, "m2.svg"),
    "startup": os.path.join(CENSOR_SOUND_DIR, "m3.svg"),
    "working": os.path.join(CENSOR_SOUND_DIR, "m4.svg"),
    "success": os.path.join(CENSOR_SOUND_DIR, "m4-.svg"),
    "drag": os.path.join(CENSOR_SOUND_DIR, "m5.svg"),
}
MASCOT_MIN_DISPLAY_SIZE = (550, 550)

FIXED_WINDOW_WIDTH = 1350
CONTROLS_COLUMN_WIDTH = 640
FIXED_WINDOW_HEIGHT = 770

MASCOT_AREA_WIDTH = FIXED_WINDOW_WIDTH - CONTROLS_COLUMN_WIDTH

MASCOT_AREA_HEIGHT = 600



def calculate_toxicity_score(text: str) -> float: #-------------------------------------------------------------------------------------------------------------------------
    if 'torch' not in sys.modules or 'transformers' not in sys.modules or len(text.split()) < MIN_TOXICITY_WORD_COUNT:
        return 0.0

    global TOXICITY_MODEL, TOXICITY_TOKENIZER, TOXICITY_DEVICE

    if TOXICITY_MODEL is None or TOXICITY_TOKENIZER is None:
        return 0.0

    inputs = TOXICITY_TOKENIZER(text, return_tensors="pt", truncation=True, padding=True)

    inputs = {k: v.to(TOXICITY_DEVICE) for k, v in inputs.items()}

    TOXICITY_MODEL.eval()

    is_cuda = (TOXICITY_DEVICE.type == 'cuda')
    with torch.autocast(device_type=TOXICITY_DEVICE.type, dtype=torch.float16, enabled=is_cuda):
        with torch.no_grad():
            outputs = TOXICITY_MODEL(**inputs)

    probabilities = F.softmax(outputs.logits, dim=-1)

    toxic_index = TOXICITY_MODEL.config.label2id.get('toxic')

    if toxic_index is not None and probabilities.size(1) > toxic_index:
        toxic_score = probabilities[0][toxic_index].float().item()
    else:
        toxic_score = 0.5

    return toxic_score

def normalize_text_for_profanity(word: str) -> str: #------------------------------------------------------------------------------------------------------------------------
    
    word = word.lower()

    word = word.replace('0', 'o').replace('1', 'i').replace('!', 'i').replace('3', 'e').replace('4', 'a')
    word = word.replace('5', 's').replace('7', 't').replace('8', 'b').replace('$', 's').replace('@', 'a').replace('|', 'i').replace('^', 'a')

    word = word.replace('ph', 'f')

    word = re.sub(r'[^a-z]', '', word)

    if len(word) <= 1:
        return ""

    return word

def check_for_profanity(word: str, use_obfuscation_check: bool) -> bool: #---------------------------------------------------------------------------------------------
    
    if 'better_profanity' not in sys.modules:
        return False
        
    global GLOBAL_WHITELIST_WORDS, GLOBAL_BLACKLIST_WORDS

    normalized_word = normalize_text_for_profanity(word)
    
    if normalized_word and normalized_word in GLOBAL_WHITELIST_WORDS:
        return False

    # Inflection whitelist match: check if the base/root of the word is whitelisted
    if normalized_word:
        _SUFFIXES = ('ing', 'ings', 'tion', 'tions', 'ed', 'er', 'ers', 'est', 'ly', 'ish', 'ness', 's')
        for suffix in _SUFFIXES:
            if normalized_word.endswith(suffix):
                root = normalized_word[:-len(suffix)]
                if len(root) >= 3 and root in GLOBAL_WHITELIST_WORDS:
                    return False

    if normalized_word and normalized_word in GLOBAL_BLACKLIST_WORDS:
        return True

    # 1. Check original word (for standard lexicon match)
    if profanity.contains_profanity(word):
        return True

    # 2. Check normalized word (for obfuscation/Leet speak match)
    if use_obfuscation_check:
        if profanity.contains_profanity(normalized_word):
            return True

    return False

def format_censored_word(word: str, censor_style: str, custom_replacement: str) -> str: #-------------------------------------------------------------------------------------------
    
    if censor_style == 'A':
        return '*' * len(word)
    elif censor_style == 'B':
        if len(word) > 0:
            return word[0] + ('*' * max(1, len(word) - 1))
        return '*'
    elif censor_style == 'D':
        return custom_replacement
    
    return '****'


def read_text_file(file_path: str) -> str: #-----------------------------------------------------------------------------------------------------------------------------------------
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.txt':
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                return ""
        return ""
    elif ext == '.docx':
        try:
            document = docx.Document(file_path)
            return "\n".join(filter(None, [paragraph.text for paragraph in document.paragraphs]))
        except Exception:
            return ""
    else:
        return ""

def load_word_list_from_text(text_content: str) -> Set[str]:
    
    if not text_content:
        return set()
    
    words = re.findall(r'\S+', text_content)
    
    normalized_words = set()
    for word in words:
        if word.strip():
            normalized_word = normalize_text_for_profanity(word.strip())
            if normalized_word:
                normalized_words.add(normalized_word)
                
    return normalized_words

def pre_convert_to_wav(input_path: str, progress_callback: Callable) -> str:
    
    if 'pydub' not in sys.modules:
        progress_callback.emit("pydub not imported. Skipping pre-conversion.")
        return input_path
        
    base_name, ext = os.path.splitext(input_path)
    ext = ext.lower()

    if ext not in ['.mp4', '.mov', '.mkv', '.m4a']:
        return input_path

    temp_wav_path = f"{base_name}_temp_VAD_in.wav"

    progress_callback.emit(f"Pre-converting {ext} to WAV for VAD/ASR compatibility...")

    try:
        audio_segment = AudioSegment.from_file(input_path)

        audio_segment = audio_segment.set_frame_rate(VAD_SAMPLE_RATE).set_channels(1)

        audio_segment.export(temp_wav_path, format="wav")

        progress_callback.emit(f"Pre-conversion successful. Using temporary file: {os.path.basename(temp_wav_path)}")
        return temp_wav_path

    except Exception as e:
        progress_callback.emit(f"Pre-conversion failed: {e}. VAD may still fail. Ensure FFmpeg is installed and on your PATH.")
        return input_path

class Stream(object):
    
    def __init__(self, callback: Callable):
        self.callback = callback
        self.line_buffer = ""
        
    def isatty(self):
        return False

    def write(self, text):
        
        if '\r' in text:
            text = text.split('\r')[-1]

        self.line_buffer += text
        
        if '\n' in self.line_buffer:
            lines = self.line_buffer.split('\n')
            for line in lines[:-1]:
                if line.strip():
                    self.callback.emit(line.strip())
            self.line_buffer = lines[-1]
            
        elif '|' in self.line_buffer and 'M/s' in self.line_buffer and self.line_buffer.strip():
            self.callback.emit(self.line_buffer.strip())
            self.line_buffer = ""
            
    def flush(self):
        
        if self.line_buffer.strip():
            self.callback.emit(self.line_buffer.strip())
        self.line_buffer = ""

def load_ml_resources(progress_callback: Callable, load_toxicity: bool, asr_model_name: str):
    
    if 'whisper' not in sys.modules or 'torch' not in sys.modules:
        raise Exception("Core ML libraries (whisper, torch) are not installed. Cannot proceed.")
        
    global TOXICITY_MODEL, TOXICITY_TOKENIZER, TOXICITY_DEVICE, VAD_MODEL, VAD_UTILS_REFERENCE, ML_MODEL_CACHE, ASR_MODEL_KEY_CURRENT

    original_stdout = sys.stdout

    log_stream = Stream(progress_callback)
    
    try:
        sys.stdout = log_stream
        
        if asr_model_name:
            if asr_model_name in ML_MODEL_CACHE:
                progress_callback.emit(f"ASR Model ({asr_model_name}) found in cache. Ready.")
                ASR_MODEL_KEY_CURRENT = asr_model_name
            else:
                try:
                    progress_callback.emit(f"Loading/Downloading ASR model ({asr_model_name} English), if the model is your first time to use, we will download it rn, then you can use the model as you like twin, if not, then nvm")
                    model = whisper.load_model(asr_model_name)
                    ML_MODEL_CACHE[asr_model_name] = model
                    ASR_MODEL_KEY_CURRENT = asr_model_name
                    progress_callback.emit(f"ASR Model ({asr_model_name}) loaded successfully, let's go")
                except Exception as e:
                    sys.stdout = original_stdout
                    raise Exception(f"Failed to load ASR Model: {e}. Check Whisper/PyTorch installation.")

        if load_toxicity and TOXICITY_MODEL is None:
            try:
                progress_callback.emit(f"Loading/Downloading ML Toxicity Model (unitary/toxic-bert) on {TOXICITY_DEVICE}, for first time using a model, it should be installed")
                model_name = "unitary/toxic-bert"
                TOXICITY_TOKENIZER = AutoTokenizer.from_pretrained(model_name)
                TOXICITY_MODEL = AutoModelForSequenceClassification.from_pretrained(model_name)
                TOXICITY_MODEL.to(TOXICITY_DEVICE)
                progress_callback.emit("ML Toxicity Model loaded successfully, we're back")
            except Exception as e:
                sys.stdout = original_stdout
                raise Exception(f"Failed to load REAL ML Toxicity Model. Check 'torch'/'transformers' installation. Error: {e}")
        elif not load_toxicity and TOXICITY_MODEL is None:
            pass

        if VAD_MODEL is None and asr_model_name:
            try:
                progress_callback.emit("Loading/Downloading VAD model (Speech filtering), its only one time installtion")
                VAD_MODEL, VAD_UTILS_CONTAINER = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    trust_repo=True
                )

                if isinstance(VAD_UTILS_CONTAINER, tuple):
                    VAD_UTILS_REFERENCE = VAD_UTILS_CONTAINER[1]
                else:
                    VAD_UTILS_REFERENCE = VAD_UTILS_CONTAINER

                VAD_MODEL.to(TOXICITY_DEVICE)
                progress_callback.emit("VAD Model loaded successfully.")
            except Exception as e:
                sys.stdout = original_stdout
                raise Exception(f"Failed to load VAD model. Error: {e}")

    finally:
        sys.stdout = original_stdout

def apply_vad_filtering(input_path: str, progress_callback: Callable) -> str:
    
    if 'torchaudio' not in sys.modules or 'pydub' not in sys.modules:
        progress_callback.emit("torchaudio or pydub not imported. Skipping VAD filtering.")
        return input_path
        
    global VAD_MODEL, VAD_SAMPLE_RATE, TOXICITY_DEVICE, VAD_UTILS_REFERENCE

    if VAD_MODEL is None:
        return input_path

    base_name, _ = os.path.splitext(input_path)
    cleaned_path = f"{base_name}_CLEANED_VAD.wav"

    progress_callback.emit(f"Applying VAD to filter speech segments...")

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="In 2.9, this function's implementation will be changed to use torchaudio.load with torchcodec")
            audio_tensor, sr = torchaudio.load(input_path)

        if sr != VAD_SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(sr, VAD_SAMPLE_RATE)
            audio_tensor = resampler(audio_tensor)
            sr = VAD_SAMPLE_RATE

        if audio_tensor.shape[0] > 1:
            audio_tensor = torch.mean(audio_tensor, dim=0, keepdim=True)

        audio_tensor = audio_tensor.to(TOXICITY_DEVICE)

        try:
            get_speech_timestamps = VAD_UTILS_REFERENCE

            if get_speech_timestamps is None or not callable(get_speech_timestamps):
                raise TypeError("'get_speech_timestamps' utility is not a callable function.")

            audio_tensor_1d = audio_tensor.squeeze(0)

            speech_timestamps = get_speech_timestamps(
                audio_tensor_1d, VAD_MODEL, sampling_rate=sr,
                chunk_size=int(0.032 * sr),
                threshold=0.5
            )

        except Exception as e:
            progress_callback.emit(f"VAD Batch Processing Utility failed: {e}. Falling back to original audio.")
            return input_path

        timestamps_ms = [
            (t['start'] * 1000, t['end'] * 1000) for t in speech_timestamps
        ]

        if not timestamps_ms:
            progress_callback.emit("VAD found no speech. Using original audio.")
            return input_path

        full_audio = AudioSegment.from_file(input_path)
        cleaned_audio = AudioSegment.empty()

        for start_ms, end_ms in timestamps_ms:
            start_ms = max(0, start_ms)
            end_ms = min(len(full_audio), end_ms)

            chunk = full_audio[start_ms:end_ms]
            cleaned_audio += chunk

        total_duration = len(full_audio)

        progress_callback.emit(f"VAD filtered original audio ({total_duration/1000:.1f}s) down to {len(cleaned_audio)/1000:.1f}s of pure speech.")

        cleaned_audio.export(cleaned_path, format="wav")
        return cleaned_path

    except Exception as e:
        progress_callback.emit(f"VAD Filtering failed during processing: {e}. Falling back to original audio.")
        return input_path


def transcribe_audio(audio_path: str, progress_callback: Callable) -> Dict[str, Any]:
    if 'whisper' not in sys.modules:
        raise Exception("Whisper ASR library not imported. Cannot transcribe.")
        
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found at: {audio_path}")

    global ML_MODEL_CACHE, ASR_MODEL_KEY_CURRENT

    asr_model = ML_MODEL_CACHE.get(ASR_MODEL_KEY_CURRENT)
    if asr_model is None:
        raise Exception(f"ASR Model ('{ASR_MODEL_KEY_CURRENT}') not loaded. This shouldn't happen.")
        
    progress_callback.emit("Starting audio transcription ( This may take time, maybe you should read a book lol )")

    import warnings
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

    result = asr_model.transcribe(
        audio_path,
        language="en",
        word_timestamps=True,
        verbose=False
    )

    return result

def format_time_srt(ms: int) -> str:
    
    hours = int(ms / 3600000)
    ms -= hours * 3600000
    minutes = int(ms / 60000)
    ms -= minutes * 60000
    seconds = int(ms / 1000)
    ms -= seconds * 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


def generate_conversation_log(transcription_result: Dict[str, Any], toxicity_threshold: float, check_toxicity: bool) -> List[Dict[str, Any]]:
    
    conversation_log = []

    for segment in transcription_result.get("segments", []):
        segment_text = segment.get('text', '').strip()

        toxicity_score = 0.0
        is_toxic = False

        if check_toxicity:
            toxicity_score = calculate_toxicity_score(segment_text)
            is_toxic = toxicity_score >= toxicity_threshold

        for word_info in segment.get("words", []):
            if isinstance(word_info, dict) and 'word' in word_info:
                word = word_info['word'].strip()
                start = word_info['start']
                end = word_info['end']
            else:
                continue

            is_profane = check_for_profanity(word, use_obfuscation_check=True)

            log_entry = {
                "start_ms": int(start * 1000),
                "end_ms": int(end * 1000),
                "word": word,
                "is_profane": is_profane,
                "is_toxic": is_toxic,
                "toxicity_score": round(toxicity_score, 4),
            }
            conversation_log.append(log_entry)

    return conversation_log

def generate_beep_segment(duration_ms: int, sample_rate: int, channels: int) -> AudioSegment:
    BEEP_FREQUENCY = 1000
    n_frames = int(duration_ms * sample_rate / 1000)
    t = np.linspace(0, duration_ms / 1000, n_frames, endpoint=False)
    amplitude = np.iinfo(np.int16).max * 0.5
    beep_wave = (amplitude * np.sin(2 * np.pi * BEEP_FREQUENCY * t)).astype(np.int16)

    if channels == 2:
        beep_wave = np.column_stack((beep_wave, beep_wave)).flatten()

    return AudioSegment(
        beep_wave.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=channels
    )

def load_censor_sound(sound_choice: str, duration_ms: int, sample_rate: int, channels: int, custom_sound_path: str, volume_change: float, progress_callback) -> AudioSegment:
    if 'pydub' not in sys.modules:
        return AudioSegment.silent(duration=duration_ms)
        
    if sound_choice == 'B':
        return generate_beep_segment(duration_ms, sample_rate, channels) + volume_change

    elif sound_choice in ['D', 'Q', 'T', 'C']:
        if sound_choice == 'C' and custom_sound_path and os.path.exists(custom_sound_path):
            sound_path = custom_sound_path
        elif sound_choice == 'D':
            sound_path = DOLPHIN_SOUND_PATH
        elif sound_choice == 'Q':
            sound_path = QUACK_SOUND_PATH
        else:
            sound_path = TRIGGERED_SOUND_PATH


        if not os.path.exists(sound_path):
            progress_callback.emit(f"Warning: Sound file '{os.path.basename(sound_path)}' not found. Falling back to Beep.")
            return generate_beep_segment(duration_ms, sample_rate, channels) + volume_change

        try:
            censor_sound = AudioSegment.from_file(sound_path)
            censor_sound = censor_sound.set_frame_rate(sample_rate).set_channels(channels)

            if len(censor_sound) < duration_ms:
                repeat_count = int(np.ceil(duration_ms / len(censor_sound)))
                censor_sound = censor_sound * repeat_count

            return censor_sound[:duration_ms] + volume_change

        except Exception as e:
            progress_callback.emit(f"Error loading custom sound: {e}. Falling back to Beep.")
            return generate_beep_segment(duration_ms, sample_rate, channels) + volume_change

    return AudioSegment.silent(duration=duration_ms)

def censor_media(input_path: str, output_path_base: str, log: List[Dict[str, Any]], mode: str, censor_toxic: bool, sound_choice: str, custom_sound_path: str, volume_change: float, progress_callback: Callable, progress_value_callback: Callable) -> str:
    if 'pydub' not in sys.modules:
        raise Exception("pydub (requires FFmpeg) is not installed. Media censoring cannot proceed.")
        
    progress_callback.emit(f"Starting Media Censoring: Mode='{mode}', Censor Toxic='{censor_toxic}'...")

    def needs_censoring(entry):
        if entry['is_profane']:
            return True
        if censor_toxic and entry['is_toxic']:
            return True
        return False

    segments_to_censor = [entry for entry in log if needs_censoring(entry)]

    base_name, ext = os.path.splitext(input_path)
    censor_label = "_CENSORED"
    if censor_toxic:
        censor_label += "_TOXIC"

    output_format = ext[1:].lower()
    output_file_path = f"{base_name}{censor_label}{ext}"
    
    export_parameters = []
    
    is_video_input = output_format in ['mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v']

    if is_video_input:
        output_format = ext[1:].lower()
        output_file_path = f"{base_name}{censor_label}{ext}"
        progress_callback.emit(f"Input is video ({output_format}). Setting up two-input FFmpeg muxing (Censored Audio + Original Video).")
        
        export_parameters.extend(["-i", input_path])
        
        # NOTE: This part assumes the AudioSegment export will create a temporary audio file,
        # which will be passed as the second input (index 1) to FFmpeg in the pydub export.
        # This requires pydub's underlying logic to handle the multi-input/muxing properly.
        # This is a complex step usually handled better by native FFmpeg calls, but we rely on pydub for simplicity here.
        # For pydub's .export to handle multi-input, it needs to be configured correctly.
        # The common pydub workaround is to export the audio first, and then run a separate FFmpeg call for muxing.
        # To keep it within the single .export call (as the code seems to intend), we stick to the parameters below, 
        # but acknowledge the pydub dependency complexity.
        
        export_parameters.extend(["-map", "0:a", "-map", "1:v", "-c:v", "copy"])

    
    if not segments_to_censor:
        progress_callback.emit("No segments found requiring censorship. Finished.")
        
        if is_video_input:
            try:
                import shutil
                shutil.copyfile(input_path, output_file_path)
            except Exception as e:
                progress_callback.emit(f"Error copying video file: {e}. Output not saved.")
        return output_file_path

    try:
        media = AudioSegment.from_file(input_path)
    except Exception as e:
        raise Exception(f"Could not load media file with pydub. Ensure FFmpeg is on PATH. Error: {e}")

    bleeped_media = media[:]

    total_segments = len(segments_to_censor)

    for i, entry in enumerate(segments_to_censor):
        start = entry['start_ms']
        end = entry['end_ms']

        BUFFER_MS = 50
        actual_start = max(0, start - BUFFER_MS)
        actual_end = min(len(media), end + BUFFER_MS)
        actual_duration = actual_end - actual_start

        if actual_duration > 0:

            if mode == 'sound':
                replacement_segment = load_censor_sound(
                    sound_choice, actual_duration, media.frame_rate, media.channels, custom_sound_path, volume_change, progress_callback
                )
            elif mode == 'silence':
                replacement_segment = AudioSegment.silent(duration=actual_duration, frame_rate=media.frame_rate)
            else:
                continue

            bleeped_media = (
                bleeped_media[:actual_start] +
                replacement_segment +
                bleeped_media[actual_end:]
            )

            flag_type = "Profanity" if entry['is_profane'] else "Toxicity"
            progress_callback.emit(f"Applied '{mode}' to {flag_type} at {actual_start/1000:.2f}s")

        progress_value_callback.emit(int(50 + (i / total_segments) * 50))

    bleeped_media.export(output_file_path, format=output_format, parameters=export_parameters)
    
    progress_callback.emit(f"✅ Censored media saved successfully to: {output_file_path}")
    progress_value_callback.emit(100)
    return output_file_path

def generate_srt_file(transcription_result: Dict[str, Any], full_log: List[Dict[str, Any]], file_path: str, censor_profane: bool) -> str:
    # --- MODIFICATION START: Removed MIN_SEGMENT_DURATION_MS filter ---
    base_name, _ = os.path.splitext(file_path)
    suffix = "_transcript_CLEAN.srt" if censor_profane else "_transcript_RAW.srt"
    output_path = f"{base_name}{suffix}"

    profanity_map = {}
    # Use the full log to map profanity status by word timestamp
    for entry in full_log:
        profanity_map[(entry['start_ms'], entry['end_ms'], entry['word'])] = entry['is_profane']

    srt_content = []

    srt_index = 1
    for segment in transcription_result.get("segments", []):
        start_ms = int(segment.get('start', 0.0) * 1000)
        end_ms = int(segment.get('end', 0.0) * 1000)

        segment_words = []
        is_segment_empty = True # Check if any word was actually added

        for word_info in segment.get("words", []):
            if isinstance(word_info, dict) and 'word' in word_info:
                word = word_info['word'].strip()
                w_start_ms = int(word_info['start'] * 1000)
                w_end_ms = int(word_info['end'] * 1000)
            else:
                continue

            is_profane = profanity_map.get((w_start_ms, w_end_ms, word), False)

            if censor_profane and is_profane:
                segment_words.append(MEDIA_TRANSCRIPT_REPLACEMENT)
            else:
                segment_words.append(word)
                
            is_segment_empty = False # A transcribed word was processed

        text = " ".join(segment_words).strip()

        # REMOVED original check: if end_ms - start_ms >= MIN_SEGMENT_DURATION_MS and text:
        # NEW check: Only proceed if there is non-empty text (which ensures all words are present)
        if text and not is_segment_empty:
            srt_content.append(f"{srt_index}")
            srt_content.append(f"{format_time_srt(start_ms)} --> {format_time_srt(end_ms)}")
            srt_content.append(f"{text}\n")
            srt_index += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(srt_content))

    return output_path
    # --- MODIFICATION END ---

def generate_plain_text_file(transcription_result: Dict[str, Any], full_log: List[Dict[str, Any]], file_path: str, censor_profane: bool) -> str:
    base_name, _ = os.path.splitext(file_path)
    suffix = "_conversation_CLEAN.txt" if censor_profane else "_conversation_RAW.txt"
    output_path = f"{base_name}{suffix}"

    profanity_map = {}
    for entry in full_log:
        profanity_map[(entry['start_ms'], entry['end_ms'], entry['word'])] = entry['is_profane']

    final_text_lines = []

    for segment in transcription_result.get("segments", []):
        segment_words = []
        for word_info in segment.get("words", []):
            if isinstance(word_info, dict) and 'word' in word_info:
                word = word_info['word'].strip()
                w_start_ms = int(word_info['start'] * 1000)
                w_end_ms = int(word_info['end'] * 1000)
            else:
                continue

            is_profane = profanity_map.get((w_start_ms, w_end_ms, word), False)

            if censor_profane and is_profane:
                segment_words.append(MEDIA_TRANSCRIPT_REPLACEMENT)
            else:
                segment_words.append(word)

        if segment_words:
            final_text_lines.append(" ".join(segment_words).strip())

    text_content = "\n".join(final_text_lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text_content)

    return output_path


