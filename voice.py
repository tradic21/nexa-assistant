import os
import json
import time
import queue
import audioop
import threading

import sounddevice as sd
import speech_recognition as sr
from vosk import Model, KaldiRecognizer


try:
    import pythoncom
    import win32com.client
except ImportError:
    pythoncom = None
    win32com = None


class VoiceAssistant:
    def __init__(self, vosk_model_path, stop_event):
        self.vosk_model_path = vosk_model_path
        self.stop_event = stop_event
        self.vosk_model = None
        self.tts_cancel_event = threading.Event()
        self.wake_phrases = [
            "hey nexa",
            "hi nexa",
            "okay nexa",
            "hey nexus",
            "hi nexus",
            "hey alexa",
            "hey neka",
            "hey nesa",
            "hey nessa",
            "hey nixa",
            "hey niksa",
            "hey next",
            "hey necks",
            "hey nasa"
        ]
        self.command_phrases = [
            "open this",
            "open that",
            "select this",
            "select that",
            "show options",
            "show option",
            "open options",
            "open menu",
            "right click this",
            "right click that",
            "start dragging",
            "start drag",
            "drag this",
            "grab this",
            "pick this up",
            "drop here",
            "drop this",
            "release this",
            "stop dragging",
            "scroll up",
            "scroll down",
            "open google maps",
            "open maps",
            "open youtube",
            "open google",
            "open calculator",
            "open notepad",
            "open notebook",
            "open note pad",
            "show desktop",
            "show the desktop",
            "show my desktop",
            "go to desktop",
            "take screenshot",
            "stop listening",
            "stop talking",
            "stop speaking",
            "be quiet",
            "quiet",
            "stop action",
            "cancel action",
            "cancel current action",
            "stop current action",
            "what time is it",
            "what is the time",
            "what is the date",
            "what's the date",
            "today's date",
            "what date is it",
            "weather",
            "forecast",
            "search",
            "ask nexa",
            "ask nexus",
            "chat",
            "talk to nexa",
            "talk to nexus"
        ]

        if not os.path.exists(self.vosk_model_path):
            raise FileNotFoundError(
                f"Vosk model folder not found: {self.vosk_model_path}"
            )

    def get_vosk_model(self):
        if self.vosk_model is None:
            self.vosk_model = Model(self.vosk_model_path)

        return self.vosk_model

    def clean_vosk_text(self, text):
        return " ".join(
            text.replace("[unk]", "").strip().lower().split()
        )

    def listen_for_wake_word(self, should_keep_listening=None):
        audio_queue = queue.Queue()
        model = self.get_vosk_model()

        grammar = json.dumps(self.wake_phrases + ["[unk]"])

        recognizer = KaldiRecognizer(model, 16000, grammar)

        def audio_callback(indata, frames, time_info, status):
            if status:
                print("Wake word status:", status)

            audio_queue.put(bytes(indata))

        speech_rms_threshold = 220
        silence_rms_threshold = 120
        max_phrase_duration = 3.0
        silence_timeout = 0.9

        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=2000,
                dtype="int16",
                channels=1,
                callback=audio_callback
            ):
                in_speech = False
                speech_start_time = None
                last_voice_time = None

                while not self.stop_event.is_set():
                    if should_keep_listening and not should_keep_listening():
                        return False

                    try:
                        data = audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if should_keep_listening and not should_keep_listening():
                        return False

                    rms = audioop.rms(data, 2)

                    if not in_speech:
                        if rms >= speech_rms_threshold:
                            in_speech = True
                            speech_start_time = time.time()
                            last_voice_time = time.time()

                            recognizer = KaldiRecognizer(model, 16000, grammar)
                            recognizer.AcceptWaveform(data)

                        continue

                    recognizer.AcceptWaveform(data)

                    if rms >= silence_rms_threshold:
                        last_voice_time = time.time()

                    phrase_too_long = (
                        time.time() - speech_start_time
                    ) > max_phrase_duration

                    silence_detected = (
                        time.time() - last_voice_time
                    ) > silence_timeout

                    if phrase_too_long or silence_detected:
                        result = json.loads(recognizer.FinalResult())

                        text = result.get("text", "").strip().lower()
                        cleaned_text = self.clean_vosk_text(text)

                        print("WAKE FINAL:", repr(cleaned_text))

                        in_speech = False
                        speech_start_time = None
                        last_voice_time = None

                        if cleaned_text in self.wake_phrases:
                            return True

                return False

        except Exception as e:
            print("Wake word Vosk error:", e)
            return False

    def listen_for_command_vosk(self, on_ready=None):
        audio_queue = queue.Queue()
        model = self.get_vosk_model()
        grammar = json.dumps(self.command_phrases + ["[unk]"])
        recognizer = KaldiRecognizer(model, 16000, grammar)

        def audio_callback(indata, frames, time_info, status):
            if status:
                print("Command status:", status)

            audio_queue.put(bytes(indata))

        speech_rms_threshold = 220
        silence_rms_threshold = 120
        max_phrase_duration = 3.0
        silence_timeout = 0.8
        listen_timeout = 6.0

        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=1600,
                dtype="int16",
                channels=1,
                callback=audio_callback
            ):
                if on_ready:
                    on_ready()

                in_speech = False
                speech_start_time = None
                last_voice_time = None
                listen_started_at = time.time()

                while not self.stop_event.is_set():
                    if time.time() - listen_started_at > listen_timeout:
                        return {
                            "status": "timeout",
                            "command": None
                        }

                    try:
                        data = audio_queue.get(timeout=0.25)
                    except queue.Empty:
                        continue

                    rms = audioop.rms(data, 2)

                    if not in_speech:
                        if rms >= speech_rms_threshold:
                            in_speech = True
                            speech_start_time = time.time()
                            last_voice_time = time.time()
                            recognizer = KaldiRecognizer(model, 16000, grammar)
                            recognizer.AcceptWaveform(data)

                        continue

                    recognizer.AcceptWaveform(data)

                    if rms >= silence_rms_threshold:
                        last_voice_time = time.time()

                    phrase_too_long = (
                        time.time() - speech_start_time
                    ) > max_phrase_duration

                    silence_detected = (
                        time.time() - last_voice_time
                    ) > silence_timeout

                    if phrase_too_long or silence_detected:
                        result = json.loads(recognizer.FinalResult())
                        text = self.clean_vosk_text(result.get("text", ""))

                        print("VOSK COMMAND RAW:", repr(text))

                        if text:
                            return {
                                "status": "recognized",
                                "command": text
                            }

                        return {
                            "status": "unknown_audio",
                            "command": None
                        }

                return {
                    "status": "timeout",
                    "command": None
                }

        except Exception as e:
            print("Command Vosk error:", e)
            return {
                "status": "microphone_error",
                "command": str(e)
            }

    def listen_for_command(self, on_ready=None):
        recognizer = sr.Recognizer()

        recognizer.energy_threshold = 250
        recognizer.dynamic_energy_threshold = False
        recognizer.pause_threshold = 0.8
        recognizer.non_speaking_duration = 0.3

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)

                if on_ready:
                    on_ready()
                    time.sleep(0.35)

                audio = recognizer.listen(
                    source,
                    timeout=6,
                    phrase_time_limit=5
                )

                text = recognizer.recognize_google(
                    audio,
                    language="en-US"
                )

                text = text.strip().lower()

                print("GOOGLE COMMAND RAW:", text)

                return {
                    "status": "recognized",
                    "command": text
                }

        except sr.WaitTimeoutError:
            return {
                "status": "timeout",
                "command": None
            }

        except sr.UnknownValueError:
            return {
                "status": "unknown_audio",
                "command": None
            }

        except sr.RequestError as e:
            return {
                "status": "service_error",
                "command": str(e)
            }

        except Exception as e:
            return {
                "status": "microphone_error",
                "command": str(e)
            }

    def listen_for_search_text_google(
        self,
        timeout=6,
        phrase_time_limit=5,
        pause_threshold=0.8,
        ambient_noise_duration=0.8,
        on_ready=None
    ):
        recognizer = sr.Recognizer()

        recognizer.energy_threshold = 250
        recognizer.dynamic_energy_threshold = False
        recognizer.pause_threshold = pause_threshold
        recognizer.non_speaking_duration = 0.3

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(
                    source,
                    duration=ambient_noise_duration
                )

                if on_ready:
                    on_ready()
                    time.sleep(0.35)

                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                text = recognizer.recognize_google(
                    audio,
                    language="en-US"
                )

                text = text.strip()

                print("Google search text:", text)

                normalized = text.lower().strip()

                if "stop listening" in normalized:
                    return {
                        "status": "cancelled",
                        "text": None
                    }

                return {
                    "status": "recognized",
                    "text": text
                }

        except sr.WaitTimeoutError:
            print("Google search text timeout")

            return {
                "status": "timeout",
                "text": None
            }

        except sr.UnknownValueError:
            print("Google could not understand search text")

            return {
                "status": "unknown_audio",
                "text": None
            }

        except sr.RequestError as e:
            print("Google speech error:", e)

            return {
                "status": "service_error",
                "text": str(e)
            }

        except Exception as e:
            print("Microphone error:", e)

            return {
                "status": "microphone_error",
                "text": str(e)
            }

    def normalize_command(self, command):
        command = command.lower().strip()
        command = command.replace("[unk]", "")
        command = command.replace("  ", " ")

        return command.strip()

    def contains_nexa_name(self, command):
        name_variants = [
            "nexa",
            "nexus",
            "neka",
            "nesa",
            "nessa",
            "nixa",
            "niksa",
            "necks",
            "next",
            "nasa",
            "alexa"
        ]

        return any(name in command for name in name_variants)

    def is_show_desktop_command(self, command):
        direct_phrases = [
            "show desktop",
            "show the desktop",
            "show my desktop",
            "show desk",
            "show the desk",
            "show my desk",
            "go to desktop",
            "go desktop",
            "open desktop",
            "display desktop",
            "display desk",
            "desktop"
        ]

        if any(phrase in command for phrase in direct_phrases):
            return True

        words = set(command.split())
        return (
            ("show" in words or "display" in words or "go" in words)
            and ("desktop" in words or "desk" in words or "deskop" in words)
        )

    def classify_command(self, command):
        command = self.normalize_command(command)

        if any(p in command for p in ["stop talking", "stop speaking", "be quiet", "quiet"]):
            return "stop_talking"

        if any(p in command for p in ["stop action", "cancel action", "cancel current action", "stop current action"]):
            return "stop_action"

        if any(p in command for p in ["open this", "open that"]):
            return "open_this"

        if any(p in command for p in ["select this", "select that"]):
            return "select_this"

        if any(p in command for p in ["show options", "show option", "open options", "open menu", "right click this", "right click that"]):
            return "show_options"

        if any(p in command for p in ["start dragging", "start drag", "drag this", "grab this", "pick this up"]):
            return "start_dragging"

        if any(p in command for p in ["drop here", "drop this", "release this", "stop dragging"]):
            return "drop_here"

        if "scroll up" in command:
            return "scroll_up"

        if "scroll down" in command:
            return "scroll_down"

        if any(p in command for p in ["open google maps", "open maps"]):
            return "open_google_maps"

        elif "open youtube" in command:
            return "open_youtube"

        elif "open google" in command or "open gogle" in command:
            return "open_google"

        elif "open calculator" in command:
            return "open_calculator"

        elif any(p in command for p in ["open notepad", "open notebook", "open note pad"]):
            return "open_notepad"

        elif self.is_show_desktop_command(command):
            return "show_desktop"

        elif "take screenshot" in command:
            return "take_screenshot"

        elif "stop listening" in command:
            return "stop_listening"

        elif any(p in command for p in ["what time is it", "what is the time"]):
            return "time"

        elif any(
            p in command
            for p in [
                "what is the date",
                "what's the date",
                "today's date",
                "what date is it"
            ]
        ):
            return "date"

        elif "weather" in command or "forecast" in command:
            return "weather"

        elif command == "search":
            return "search"
        
        elif command in [
            "ask nexa",
            "ask nexus",
            "ask necks",
            "ask next",
            "ask neka",
            "ask nesa",
            "ask nessa",
            "ask nixa",
            "ask niksa",
            "ask nasa",
            "ask alexa",
            "chat",
            "talk to nexa",
            "talk to nexus",
            "talk to necks",
            "talk to next",
            "talk to neka",
            "talk to nesa",
            "talk to nessa",
            "talk to nixa",
            "talk to niksa",
            "talk to nasa",
            "talk to alexa"
        ] or (
            self.contains_nexa_name(command)
            and any(action in command for action in ["ask", "talk to", "chat with", "speak to"])
        ):
            return "chat"

        return "unknown"

    def stop_speaking(self):
        self.tts_cancel_event.set()

    def tts_worker(self, tts_queue):
        if pythoncom:
            pythoncom.CoInitialize()

        try:
            speaker = None

            if win32com:
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Rate = 0
                speaker.Volume = 100

            while True:
                text = tts_queue.get()

                try:
                    if text == "__stop__":
                        break

                    if speaker:
                        self.tts_cancel_event.clear()
                        speak_async = 1
                        purge_before_speak = 2

                        speaker.Speak(text, speak_async)

                        while not speaker.WaitUntilDone(50):
                            if self.tts_cancel_event.is_set():
                                speaker.Speak("", speak_async | purge_before_speak)

                                try:
                                    speaker.Skip("Sentence", 999)
                                except Exception:
                                    pass

                                break

                            time.sleep(0.05)
                    else:
                        print("TTS not available:", text)

                except Exception as e:
                    print("TTS error:", e)

                finally:
                    tts_queue.task_done()

        finally:
            if pythoncom:
                pythoncom.CoUninitialize()
