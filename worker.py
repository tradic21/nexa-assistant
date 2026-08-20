import cv2
import mediapipe as mp
import pyautogui
import threading
import queue
import time
import webbrowser
import datetime
import os
import re

from PySide6.QtCore import QThread, Signal

from gestures import GestureDetector
from voice import VoiceAssistant
from system_actions import (
    open_calculator,
    open_notepad,
    show_desktop,
    take_screenshot,
    get_weather_varazdin,
    get_current_brightness,
    set_current_brightness
)


pyautogui.PAUSE = 0

DEFAULT_CAMERA_INDEX = 0
MAX_CAMERA_INDEX_TO_TRY = 5


def get_configured_camera_index():
    configured_index = os.getenv("NEXA_CAMERA_INDEX")

    if configured_index is None:
        return DEFAULT_CAMERA_INDEX

    try:
        return int(configured_index)
    except ValueError:
        return DEFAULT_CAMERA_INDEX


def get_camera_candidates():
    candidates = [get_configured_camera_index()]
    candidates.extend(range(MAX_CAMERA_INDEX_TO_TRY + 1))

    unique_candidates = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)

    return unique_candidates


def configure_camera_capture(cap):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)


def camera_frame_is_usable(frame):
    if frame is None or frame.size == 0:
        return False

    return True


def open_usable_camera():
    for camera_index in get_camera_candidates():
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        configure_camera_capture(cap)

        if not cap.isOpened():
            cap.release()
            continue

        for _ in range(10):
            success, frame = cap.read()

            if success and camera_frame_is_usable(frame):
                return cap, camera_index

            time.sleep(0.05)

        cap.release()

    return None, None


class AssistantWorker(QThread):
    gesture_changed = Signal(str)
    voice_status_changed = Signal(str)
    last_voice_changed = Signal(str)
    chat_message_added = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.running = True

        self.voice_request_queue = queue.Queue()
        self.voice_result_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.tts_queue = queue.Queue()

        self.stop_event = threading.Event()

        self.wake_word_enabled = True
        self.camera_window_visible = True
        self.voice_drag_active = False
        self.voice_drag_started_at = None
        self.voice_drag_timeout_seconds = 15

        self.gesture_detector = GestureDetector()

        self.voice_assistant = VoiceAssistant(
            vosk_model_path="vosk-model-small-en-us-0.15",
            stop_event=self.stop_event
        )

    def request_voice_command(self):
        self.wake_word_enabled = False
        self.voice_status_changed.emit("Voice requested")
        self.voice_request_queue.put("listen")

    def request_chat_command(self):
        self.wake_word_enabled = False
        self.command_queue.put(("chat", "chat"))

    def request_chat_text(self, question):
        question = question.strip()

        if not question:
            return

        self.wake_word_enabled = False
        self.command_queue.put(("chat_text", question))

    def toggle_camera_window(self):
        self.camera_window_visible = not self.camera_window_visible

    def stop(self):
        self.running = False
        self.wake_word_enabled = False
        self.stop_event.set()

        self.release_voice_drag()

        self.voice_request_queue.put("stop")
        self.command_queue.put(("stop", None))
        self.tts_queue.put("__stop__")

    def speak(self, text, wait=False):
        self.tts_queue.put(self.clean_text_for_speech(text))

        if wait:
            self.tts_queue.join()

    def play_sound_pattern(self, pattern):
        def worker():
            try:
                import winsound

                for frequency, duration in pattern:
                    winsound.Beep(frequency, duration)
                    time.sleep(0.03)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def play_speak_now_sound(self):
        self.play_sound_pattern([(1320, 80), (1660, 90)])

    def play_error_cancel_sound(self):
        self.play_sound_pattern([(520, 100), (360, 140)])

    def play_ready_sound(self):
        self.play_sound_pattern([(880, 70), (1175, 80), (1568, 100)])

    def mark_listening_now(self):
        self.voice_status_changed.emit("Listening now...")
        self.play_speak_now_sound()

    def voice_worker(self):
        while not self.stop_event.is_set():
            try:
                request = self.voice_request_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if request == "listen":
                self.voice_result_queue.put({
                    "type": "voice_status",
                    "value": "Listening..."
                })

                result = self.voice_assistant.listen_for_command_vosk(
                    on_ready=self.play_speak_now_sound
                )

                should_try_online = result["status"] == "unknown_audio"

                if result["status"] == "recognized":
                    command = self.voice_assistant.normalize_command(
                        result["command"]
                    )
                    intent = self.voice_assistant.classify_command(command)
                    should_try_online = intent == "unknown"

                if should_try_online:
                    self.voice_result_queue.put({
                        "type": "voice_status",
                        "value": "Trying online recognition..."
                    })

                    result = self.voice_assistant.listen_for_command(
                        on_ready=None
                    )

                if result["status"] == "recognized":
                    self.voice_result_queue.put({
                        "type": "voice_command",
                        "value": result["command"]
                    })

                elif result["status"] == "timeout":
                    self.play_error_cancel_sound()
                    self.wake_word_enabled = True
                    self.voice_result_queue.put({
                        "type": "voice_status",
                        "value": "Listening timeout"
                    })

                elif result["status"] == "unknown_audio":
                    self.play_error_cancel_sound()
                    self.wake_word_enabled = True
                    self.voice_result_queue.put({
                        "type": "voice_status",
                        "value": "Could not understand audio"
                    })

                elif result["status"] == "service_error":
                    self.play_error_cancel_sound()
                    self.wake_word_enabled = True
                    self.voice_result_queue.put({
                        "type": "voice_status",
                        "value": f"Speech service error: {result['command']}"
                    })

                elif result["status"] == "microphone_error":
                    self.play_error_cancel_sound()
                    self.wake_word_enabled = True
                    self.voice_result_queue.put({
                        "type": "voice_status",
                        "value": f"Microphone error: {result['command']}"
                    })

            elif request == "stop":
                break

    def wake_word_worker(self):
        print("Vosk wake_word_worker started")
        self.last_voice_changed.emit("Wake word ready: hey nexa")

        while not self.stop_event.is_set():
            if not self.wake_word_enabled:
                time.sleep(0.1)
                continue

            detected = self.voice_assistant.listen_for_wake_word(
                should_keep_listening=lambda: self.wake_word_enabled
            )

            if self.stop_event.is_set():
                break

            if detected:
                print("Wake word detected: hey nexa")

                self.voice_result_queue.put({
                    "type": "voice_status",
                    "value": "Wake word detected"
                })

                self.wake_word_enabled = False

                try:
                    import winsound
                    winsound.Beep(1000, 180)
                except Exception:
                    pass

                self.request_voice_command()
                time.sleep(0.5)

    def command_worker(self):
        while not self.stop_event.is_set():
            try:
                intent, command = self.command_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if intent == "stop":
                break

            try:
                if intent == "chat_text":
                    self.answer_chat_question(command)
                else:
                    self.execute_voice_command(intent, command)
            finally:
                time.sleep(1.0)
                self.wake_word_enabled = True

    def process_voice_results(self):
        try:
            while True:
                message = self.voice_result_queue.get_nowait()

                if message["type"] == "voice_status":
                    self.voice_status_changed.emit(message["value"])
                    self.last_voice_changed.emit(message["value"])

                elif message["type"] == "voice_command":
                    try:
                        raw_command = message["value"]
                        command = self.voice_assistant.normalize_command(raw_command)
                        intent = self.voice_assistant.classify_command(command)

                        self.last_voice_changed.emit(command)
                        self.voice_status_changed.emit("Command recognized")

                        print("Recognized command:", command)
                        print("Classified intent:", intent)

                        self.command_queue.put((intent, command))

                    finally:
                        pass

        except queue.Empty:
            pass

    def scroll_in_steps(self, amount, steps=20, delay=0.01):
        step_amount = int(amount / steps)

        if step_amount == 0:
            step_amount = 1 if amount > 0 else -1

        for _ in range(steps):
            pyautogui.scroll(step_amount)
            time.sleep(delay)

    def release_voice_drag(self):
        if not self.voice_drag_active:
            return False

        pyautogui.mouseUp(button="left")
        self.voice_drag_active = False
        self.voice_drag_started_at = None

        return True

    def check_voice_drag_timeout(self):
        if not self.voice_drag_active or self.voice_drag_started_at is None:
            return

        if time.time() - self.voice_drag_started_at < self.voice_drag_timeout_seconds:
            return

        self.release_voice_drag()

        answer = "Dragging timed out"
        self.play_error_cancel_sound()
        self.last_voice_changed.emit(answer)
        self.voice_status_changed.emit("Action cancelled")
        self.speak(answer)
    
    def clean_text_for_speech(self, text):
        cleaned_lines = []

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            line = re.sub(r"^[-*•]+\s*", "", line)
            line = re.sub(r"^\d+[.)]\s*", "", line)

            if line and line[-1] not in ".!?:;":
                line += "."

            cleaned_lines.append(line)

        text = " ".join(cleaned_lines) if cleaned_lines else text
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"__(.*?)__", r"\1", text)
        text = text.replace("*", "")
        text = text.replace("#", "")
        text = text.replace("_", "")
        text = text.replace("`", "")
        text = text.replace("/", " or ")
        text = text.replace(" - ", ". ")
        text = text.replace("-", " ")
        text = text.replace("•", "")
        text = text.replace("•", "")
        text = text.replace(":", ".")
        text = text.replace(";", ".")
        text = " ".join(text.split())

        return text

    def clean_answer_for_chat(self, text):
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"__(.*?)__", r"\1", text)
        text = text.replace("`", "")
        text = text.replace("***", "")
        text = text.replace("**", "")

        return text.strip()
    
    def handle_chat_command(self):
        prompt_text = "What would you like to ask?"

        self.voice_status_changed.emit("Listening for question...")
        self.last_voice_changed.emit(prompt_text)
        self.speak(prompt_text, wait=True)

        time.sleep(0.6)

        question_result = self.voice_assistant.listen_for_search_text_google(
            timeout=10,
            phrase_time_limit=12,
            pause_threshold=1.2,
            ambient_noise_duration=0.3,
            on_ready=self.mark_listening_now
        )

        if question_result["status"] == "cancelled":
            self.play_error_cancel_sound()
            answer = "Chat cancelled"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Listening cancelled")
            self.speak(answer)
            return

        if question_result["status"] != "recognized":
            self.play_error_cancel_sound()
            answer = "I could not understand the question"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Chat failed")
            self.speak(answer)
            return

        question = question_result["text"]

        self.answer_chat_question(question)

    def answer_chat_question(self, question):
        self.chat_message_added.emit("You", question)

        self.last_voice_changed.emit(f"Question: {question}")
        self.voice_status_changed.emit("Generating answer...")

        answer = self.ask_llm(question)

        self.chat_message_added.emit("Nexa", answer)

        self.last_voice_changed.emit("Nexa Chat response")
        self.voice_status_changed.emit("Question answered")
        self.speak(answer)

    def answer_known_question(self, question):
        q = question.lower()

        if "chatbot" in q or "chat bot" in q:
            return (
                "A chatbot is a software assistant that communicates with users through text or voice to answer questions, provide information, or help with tasks."
            )

        asks_about_combining_inputs = (
            ("gesture" in q and "voice" in q)
            and any(
                word in q
                for word in [
                    "combine",
                    "combined",
                    "together",
                    "both",
                    "with",
                    "alongside",
                    "advantage",
                    "advantages",
                    "complement",
                    "workflow",
                    "use"
                ]
            )
        )
        asks_about_voice_problem = (
            ("voice" in q or "hear" in q or "understand" in q)
            and any(word in q for word in ["why", "not", "problem", "wrong", "misunderstand", "mistake"])
        )

        if asks_about_voice_problem:
            return (
                "Nexa might not understand a voice command if you start speaking before it is listening, "
                "if there is background noise, if the microphone is too quiet, or if the sentence is too different "
                "from the supported commands. Try waiting for the listening prompt, speak one clear command, "
                "and use phrases like open Google, take screenshot, search YouTube, or ask Nexa."
            )

        if (
            ("gesture" in q or "gestures" in q)
            and (
                "talk to nexa" in q
                or re.search(r"\bchat\b", q)
                or "ask nexa" in q
                or re.search(r"\btalk\b", q)
            )
        ):
            return (
                "Yes. You can use gestures while talking to Nexa. Gestures can keep controlling the mouse, "
                "clicks, scrolling, volume, or brightness, while voice or chat is used for questions and commands. "
                "For a question, say Hey Nexa and then say ask Nexa, chat, or talk to Nexa. You can also type in the chat."
            )

        if (
            "what can you do" in q
            or "what do you do" in q
            or "what are you able to do" in q
            or "how do i use you" in q
            or "how to use you" in q
            or "using you" in q
            or "guide for using you" in q
            or ("short guide" in q and "use" in q)
        ):
            return (
                "Here is a short guide for using Nexa. "
                "Say Hey Nexa to start a voice command. "
                "Use voice commands to open Google, YouTube, Google Maps, Calculator, Notepad, take screenshots, show the desktop, search, or ask questions. "
                "Use hand gestures to move the mouse, left click, double click, right click, scroll, drag and select, and control volume or brightness. "
                "If Nexa does not understand you, try speaking clearly and keeping your hand visible to the camera."
            )

        if (
            "what gestures" in q
            or "which gestures" in q
            or "available gestures" in q
            or "gestures can i use" in q
            or "explain all gestures" in q
            or "explain all gesture" in q
            or "all gestures" in q
            or "list gestures" in q
            or ("gesture" in q and "one by one" in q)
        ):
            return (
                "Nexa supports nine gestures. "
                "1. Neutral: an open palm with all fingers raised. It stops the current gesture. "
                "2. Move: index and middle finger raised. It moves the mouse cursor. "
                "3. Left click: only the index finger raised. It performs a left mouse click. "
                "4. Double click: index and middle finger raised close together. It performs a double click. "
                "5. Right click: thumb and pinky raised, like a shaka sign. It performs a right mouse click. "
                "6. Scroll: index, middle, and ring finger raised. Moving the hand up or down scrolls the page. "
                "7. Drag and select: a closed fist. It holds the left mouse button while you move. "
                "8. Pinch volume: thumb and index finger touching with only the index finger extended. Moving sideways changes volume. "
                "9. Pinch brightness: thumb and index finger touching with the other fingers raised. Moving up or down changes screen brightness."
            )

        if "neutral" in q:
            return (
                "The Neutral gesture is an open hand with all five fingers raised."
            )

        if "move" in q and ("gesture" in q or "mouse" in q):
            return (
                "The Move gesture looks like a V sign, with the index finger and middle finger raised."
            )

        if "left click" in q:
            return (
                "The Left click gesture has only the index finger raised."
            )

        if "double click" in q:
            return (
                "The Double click gesture has the index finger and middle finger raised close together."
            )

        if "right click" in q:
            return (
                "The Right click gesture is a shaka sign, with the thumb and pinky raised."
            )

        if "scroll" in q:
            return (
                "The Scroll gesture has three fingers raised."
            )

        if "drag" in q or "select files" in q or "drag and select" in q:
            return (
                "The Drag and select gesture is a closed fist."
            )

        if "volume" in q or "sound" in q:
            return (
                "The Pinch volume gesture has the thumb and index finger touching, with only the index finger extended. Move sideways to change volume."
            )

        if "brightness" in q:
            return (
                "The Pinch brightness gesture has the thumb and index finger touching, with the other fingers raised. Move up or down to change brightness."
            )

        if "no hand" in q:
            return (
                "No hand detected means that the camera currently does not see a hand clearly."
            )

        if "unknown" in q or "not recognized" in q:
            return (
                "Gesture not recognized means that the assistant sees a hand, but it cannot match it to one of the supported gestures."
            )

        if (
            not asks_about_combining_inputs
            and not asks_about_voice_problem
            and (
                "voice command" in q
                or "voice commands" in q
                or "commands can i use" in q
                or "available commands" in q
            )
        ):
            return (
                "You can use voice commands such as open Google, open YouTube, open Google Maps, "
                "open calculator, open Notepad, show desktop, take screenshot, what time is it, what is the date, "
                "weather, search, and ask Nexa."
            )

        if "open google maps" in q:
            return 'To open Google Maps, say "Hey Nexa" and then say "open Google Maps".'

        if "open youtube" in q:
            return 'To open YouTube, say "Hey Nexa" and then say "open YouTube".'

        if "open google" in q:
            return 'To open Google, say "Hey Nexa" and then say "open Google".'

        if "open notepad" in q or "open notebook" in q or "open note pad" in q:
            return 'To open Notepad, say "Hey Nexa" and then say "open Notepad".'

        if "search" in q or "search web" in q:
            return (
                'First open Google, YouTube, or Google Maps and place the cursor in the search field. '
                'Then say "Hey Nexa" and "search". After I ask what you want to search for, say your search phrase.'
            )

        if "screenshot" in q:
            return 'To take a screenshot, say "Hey Nexa" and then say "take screenshot".'

        if "desktop" in q:
            return 'To show the desktop, say "Hey Nexa" and then say "show desktop".'

        if "ask nexa" in q or re.search(r"\bchat\b", q) or "talk to nexa" in q:
            return (
                'To ask me a question, say "Hey Nexa" and then say "ask Nexa", "chat", or "talk to Nexa".'
            )

        if "why" in q and ("gesture" in q or "recognized" in q):
            return (
                "A gesture may not be recognized if your hand is too far from the camera, "
                "partly outside the frame, poorly lit, or if the fingers are not clearly visible."
            )

        if "why" in q and ("voice" in q or "hear" in q or "understand" in q):
            return (
                "Voice recognition can make mistakes because of background noise, unclear pronunciation, "
                "or microphone quality."
            )

        return None


    def is_question_in_scope(self, question):
        q = question.lower()

        allowed_keywords = [
            "nexa",
            "assistant",
            "chatbot",
            "chat bot",
            "gesture",
            "gestures",
            "voice",
            "command",
            "commands",
            "combine",
            "combined",
            "together",
            "control",
            "computer control",
            "control my computer",
            "hands free",
            "hands-free",
            "accessibility",
            "accessible",
            "interaction",
            "interact",
            "input",
            "input methods",
            "human computer interaction",
            "human-computer interaction",
            "interface",
            "card",
            "cards",
            "mouse",
            "click",
            "double click",
            "right click",
            "left click",
            "scroll",
            "drag",
            "select",
            "volume",
            "sound",
            "brightness",
            "screenshot",
            "desktop",
            "google",
            "youtube",
            "maps",
            "search",
            "multimodal",
            "speech",
            "hand",
            "camera",
            "microphone",
            "speech recognition",
            "wake word",
            "hey nexa",
            "using you",
            "use you",
            "short guide"
        ]

        return any(keyword in q for keyword in allowed_keywords) 
    
    def ask_llm(self, question):
        known_answer = self.answer_known_question(question)

        if known_answer is not None:
            return known_answer

        if not self.is_question_in_scope(question):
            return (
                "I am designed to help with Nexa gestures, voice commands, "
                "the assistant interface, and supported computer actions."
            )

        try:
            system_prompt = """
    You are Nexa, a multimodal assistant.

    Answer only questions related to:
    - the Nexa assistant
    - chatbots and conversational assistants
    - Nexa hand gestures
    - Nexa voice commands
    - Nexa interface
    - basic supported computer actions
    - multimodal interaction
    - accessibility and hands-free computer control
    - how voice and gesture input can be combined

    The only Nexa gestures are:
    Neutral, Move, Left click, Double click, Right click, Scroll,
    Drag and select, Pinch volume, and Pinch brightness.

    Nexa uses gestures for mouse movement, clicking, scrolling,
    drag and select, volume, and brightness. Nexa uses voice commands
    for opening Google, YouTube, Google Maps, Calculator, Notepad, showing the
    desktop, taking screenshots, checking time, date, weather, search,
    and starting chat.

    If a question is a broader conceptual question about multimodal
    interfaces, accessibility, voice input, gesture input, or computer
    control, answer it in general terms and connect it to Nexa when useful.

    If you are not sure about the answer, do not guess.
    Do not invent gestures, commands, features, or technical details.

    Keep answers short, clear, and simple. Finish the final sentence.
    Use plain text only. Do not use Markdown, bold markers, asterisks,
    tables, or headings. If you use bullets, keep them short and put each
    bullet on its own line.
    """

            if not os.getenv("OPENAI_API_KEY"):
                return "OpenAI API key is not configured."

            from openai import OpenAI

            client = OpenAI()
            model = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini")

            response = client.responses.create(
                model=model,
                instructions=system_prompt.strip(),
                input=question,
                max_output_tokens=400,
                reasoning={"effort": "none"},
            )

            answer = self.clean_answer_for_chat(response.output_text.strip())

            if not answer:
                return "I am not sure about that."

            return answer

        except Exception as e:
            print("OpenAI error:", e)
            return "I could not generate an answer right now."
    
    def execute_voice_command(self, intent, command):
        if intent == "open_google_maps":
            webbrowser.open("https://www.google.com/maps")

            answer = "Opening Google Maps"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "open_youtube":
            webbrowser.open("https://www.youtube.com")

            answer = "Opening YouTube"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "open_google":
            webbrowser.open("https://www.google.com")

            answer = "Opening Google"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "open_this":
            self.release_voice_drag()
            pyautogui.doubleClick()

            answer = "Opening selected item"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "select_this":
            self.release_voice_drag()
            pyautogui.click(button="left")

            answer = "Selected item"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "show_options":
            self.release_voice_drag()
            pyautogui.click(button="right")

            answer = "Showing options"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "start_dragging":
            if self.voice_drag_active:
                answer = "Dragging is already active"
            else:
                pyautogui.mouseDown(button="left")
                self.voice_drag_active = True
                self.voice_drag_started_at = time.time()
                answer = "Started dragging"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "drop_here":
            if self.release_voice_drag():
                answer = "Dropped item"
            else:
                answer = "No item is being dragged"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "stop_action":
            self.play_error_cancel_sound()

            if self.release_voice_drag():
                answer = "Action cancelled"
            else:
                answer = "No active action to cancel"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Action cancelled")
            self.speak(answer)

        elif intent == "stop_talking":
            self.voice_assistant.stop_speaking()
            self.play_error_cancel_sound()

            answer = "Stopped speaking"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Speech stopped")

        elif intent == "scroll_up":
            self.scroll_in_steps(600)

            answer = "Scrolling up"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "scroll_down":
            self.scroll_in_steps(-600)

            answer = "Scrolling down"
            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "open_calculator":
            if open_calculator():
                answer = "Opening Calculator"
            else:
                answer = "I could not open Calculator"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "open_notepad":
            if open_notepad():
                answer = "Opening Notepad"
            else:
                answer = "I could not open Notepad"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "show_desktop":
            if show_desktop():
                answer = "Showing desktop"
            else:
                answer = "I could not show the desktop"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "take_screenshot":
            screenshot_path = take_screenshot()

            if screenshot_path:
                answer = "Screenshot taken"
                self.last_voice_changed.emit(f"Screenshot saved: {screenshot_path}")
            else:
                answer = "I could not take a screenshot"
                self.last_voice_changed.emit(answer)

            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        elif intent == "stop_listening":
            self.release_voice_drag()
            self.play_error_cancel_sound()

            answer = "Stopping current listening"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Listening cancelled")
            self.speak(answer)

        elif intent == "time":
            now = datetime.datetime.now()

            hour_24 = now.hour
            minute = now.minute

            period = "AM" if hour_24 < 12 else "PM"

            hour_12 = hour_24 % 12
            if hour_12 == 0:
                hour_12 = 12

            if minute == 0:
                time_text = f"{hour_12} o'clock {period}"
            elif minute < 10:
                time_text = f"{hour_12} oh {minute} {period}"
            else:
                time_text = f"{hour_12} {minute} {period}"

            answer = f"It is {time_text}"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Question answered")
            self.speak(answer)

        elif intent == "date":
            now = datetime.datetime.now()

            day_name = now.strftime("%A")
            month_name = now.strftime("%B")
            day_number = now.day
            year = now.year

            answer = f"Today is {day_name}, {month_name} {day_number}, {year}"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Question answered")
            self.speak(answer)

        elif intent == "weather":
            answer = get_weather_varazdin()

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Question answered")
            self.speak(answer)
        
        elif intent == "search":
            self.handle_search_command(
                prompt_text="What would you like me to search for?",
                status_text="Listening for search text...",
                cancelled_answer="Search cancelled",
                failed_answer="Search text was not recognized",
                failed_speech="I could not understand the search text",
                success_answer_builder=lambda text: f"Searching for {text}"
            )

        elif intent == "chat":
            self.handle_chat_command()
        
        else:
            answer = f"Unknown command: {command}"

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Unknown command")
            self.speak("Sorry, I did not understand the command")

    def handle_search_command(
        self,
        prompt_text,
        status_text,
        cancelled_answer,
        failed_answer,
        failed_speech,
        success_answer_builder
    ):
        self.voice_status_changed.emit(status_text)
        self.last_voice_changed.emit(prompt_text)
        self.speak(prompt_text, wait=True)

        time.sleep(0.4)

        search_result = self.voice_assistant.listen_for_search_text_google(
            timeout=8,
            phrase_time_limit=8,
            pause_threshold=1.1,
            ambient_noise_duration=0.3,
            on_ready=self.mark_listening_now
        )

        if search_result["status"] == "cancelled":
            self.play_error_cancel_sound()
            self.last_voice_changed.emit(cancelled_answer)
            self.voice_status_changed.emit("Listening cancelled")
            self.speak(cancelled_answer)

        elif search_result["status"] == "recognized":
            search_text = search_result["text"]
            pyautogui.write(search_text, interval=0.02)
            pyautogui.press("enter")

            answer = success_answer_builder(search_text)

            self.last_voice_changed.emit(answer)
            self.voice_status_changed.emit("Command executed")
            self.speak(answer)

        else:
            self.play_error_cancel_sound()
            self.last_voice_changed.emit(failed_answer)
            self.voice_status_changed.emit("Search failed")
            self.speak(failed_speech)

    def reset_gesture_states(
        self,
        states,
        release_drag_callback
    ):
        states["left_click_frames"] = 0
        states["right_click_frames"] = 0
        states["double_click_frames"] = 0
        states["right_click_ready"] = True
        states["right_click_release_frames"] = 0

        states["move_mode_active"] = False
        states["scroll_mode_active"] = False
        states["pinch_mode_active"] = False
        states["last_pinch_type"] = None

        release_drag_callback()

    def run(self):
        voice_thread = threading.Thread(target=self.voice_worker, daemon=True)
        voice_thread.start()

        tts_thread = threading.Thread(
            target=self.voice_assistant.tts_worker,
            args=(self.tts_queue,),
            daemon=True
        )
        tts_thread.start()

        self.last_voice_changed.emit("Loading voice model...")
        self.voice_assistant.get_vosk_model()

        wake_thread = threading.Thread(target=self.wake_word_worker, daemon=True)
        wake_thread.start()

        command_thread = threading.Thread(target=self.command_worker, daemon=True)
        command_thread.start()

        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils

        screen_width, screen_height = pyautogui.size()
        camera_window_name = "Camera - Multimodal Assistant"
        camera_window_width = 480
        camera_window_height = 360
        camera_window_open = False

        self.last_voice_changed.emit("Searching for camera...")
        cap, camera_index = open_usable_camera()

        if cap is None:
            self.last_voice_changed.emit("Error: No usable camera found.")
            self.stop()

            voice_thread.join(timeout=1)
            tts_thread.join(timeout=1)
            wake_thread.join(timeout=1)
            command_thread.join(timeout=1)

            return

        self.play_ready_sound()
        self.last_voice_changed.emit(f"Using camera {camera_index}")
        self.last_voice_changed.emit("Nexa is ready")

        frame_margin_x = 70
        frame_margin_top = 70
        frame_margin_bottom = 30

        states = {
            "left_click_frames": 0,
            "right_click_frames": 0,
            "double_click_frames": 0,

            "click_threshold": 8,
            "double_click_threshold": 8,
            "right_click_rearm_threshold": 6,

            "click_cooldown": 0,
            "cooldown_frames": 12,
            "right_click_ready": True,
            "right_click_release_frames": 0,

            "move_mode_active": False,
            "move_start_finger_x": 0,
            "move_start_finger_y": 0,
            "move_start_mouse_x": 0,
            "move_start_mouse_y": 0,

            "prev_mouse_x": pyautogui.position()[0],
            "prev_mouse_y": pyautogui.position()[1],

            "relative_smoothing": 5.0,
            "move_sensitivity_x": 2.0,
            "move_sensitivity_y": 2.3,
            "dead_zone": 18,
            "mouse_jitter_threshold": 3,

            "scroll_mode_active": False,
            "scroll_start_y": 0,
            "scroll_sensitivity": 2.8,
            "scroll_dead_zone": 8,

            "drag_active": False,
            "drag_mode_active": False,
            "drag_start_hand_x": 0,
            "drag_start_hand_y": 0,
            "drag_start_mouse_x": 0,
            "drag_start_mouse_y": 0,
            "prev_drag_mouse_x": pyautogui.position()[0],
            "prev_drag_mouse_y": pyautogui.position()[1],

            "drag_hold_frames": 0,
            "drag_release_frames": 0,
            "drag_start_threshold": 8,
            "drag_release_threshold": 14,

            "drag_dead_zone": 18,
            "drag_sensitivity_x": 2.4,
            "drag_sensitivity_y": 2.7,
            "drag_smoothing": 6.5,

            "pinch_mode_active": False,
            "pinch_start_x": 0,
            "pinch_start_y": 0,

            "brightness_dead_zone": 25,
            "brightness_sensitivity": 0.2,
            "volume_dead_zone": 25,

            "last_pinch_type": None,
            "last_gesture": None
        }

        def handle_drag_release():
            states["drag_hold_frames"] = 0

            if states["drag_active"]:
                states["drag_release_frames"] += 1

                if states["drag_release_frames"] >= states["drag_release_threshold"]:
                    pyautogui.mouseUp(button="left")

                    states["drag_active"] = False
                    states["drag_mode_active"] = False
                    states["drag_release_frames"] = 0

            else:
                states["drag_mode_active"] = False
                states["drag_release_frames"] = 0

        with mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        ) as hands:

            while self.running:
                success, frame = cap.read()

                if not success:
                    break

                frame = cv2.flip(frame, 1)
                frame_height, frame_width, _ = frame.shape

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb_frame)

                gesture_text = "No hand detected"

                cv2.rectangle(
                    frame,
                    (frame_margin_x, frame_margin_top),
                    (frame_width - frame_margin_x, frame_height - frame_margin_bottom),
                    (255, 255, 0),
                    2
                )

                self.process_voice_results()
                self.check_voice_drag_timeout()

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing.DrawingSpec(
                                color=(0, 255, 0),
                                thickness=2,
                                circle_radius=4
                            ),
                            mp_drawing.DrawingSpec(
                                color=(0, 0, 255),
                                thickness=2,
                                circle_radius=2
                            )
                        )

                        landmarks = hand_landmarks.landmark

                        gesture_data = self.gesture_detector.detect(
                            landmarks,
                            frame_width,
                            frame_height
                        )

                        gesture_text = gesture_data["gesture"]

                        thumb_pos = gesture_data.get("thumb_pos")
                        index_pos = gesture_data.get("index_pos")

                        if gesture_text != "RIGHT CLICK":
                            states["right_click_release_frames"] += 1

                            if (
                                states["right_click_release_frames"]
                                >= states["right_click_rearm_threshold"]
                            ):
                                states["right_click_ready"] = True
                        else:
                            states["right_click_release_frames"] = 0

                        if thumb_pos and index_pos:
                            cv2.circle(frame, thumb_pos, 8, (255, 255, 0), cv2.FILLED)
                            cv2.circle(frame, index_pos, 8, (255, 255, 0), cv2.FILLED)
                            cv2.line(frame, thumb_pos, index_pos, (255, 255, 0), 2)

                        if gesture_text == "NEUTRAL":
                            self.reset_gesture_states(states, handle_drag_release)

                        elif gesture_text == "PINCH VOLUME":
                            if states["last_pinch_type"] != "volume":
                                states["pinch_mode_active"] = False
                                states["last_pinch_type"] = "volume"

                            states["left_click_frames"] = 0
                            states["right_click_frames"] = 0
                            states["double_click_frames"] = 0
                            states["move_mode_active"] = False
                            states["scroll_mode_active"] = False

                            handle_drag_release()

                            current_x, current_y = gesture_data["pinch_pos"]

                            if not states["pinch_mode_active"]:
                                states["pinch_mode_active"] = True
                                states["pinch_start_x"] = current_x
                                states["pinch_start_y"] = current_y

                            dx_pinch = current_x - states["pinch_start_x"]

                            if abs(dx_pinch) >= states["volume_dead_zone"]:
                                if dx_pinch > 0:
                                    pyautogui.press("volumeup")
                                else:
                                    pyautogui.press("volumedown")

                                states["pinch_start_x"] = current_x
                                states["pinch_start_y"] = current_y

                        elif gesture_text == "PINCH BRIGHTNESS":
                            if states["last_pinch_type"] != "brightness":
                                states["pinch_mode_active"] = False
                                states["last_pinch_type"] = "brightness"

                            states["left_click_frames"] = 0
                            states["right_click_frames"] = 0
                            states["double_click_frames"] = 0
                            states["move_mode_active"] = False
                            states["scroll_mode_active"] = False

                            handle_drag_release()

                            current_x, current_y = gesture_data["pinch_pos"]

                            if not states["pinch_mode_active"]:
                                states["pinch_mode_active"] = True
                                states["pinch_start_x"] = current_x
                                states["pinch_start_y"] = current_y

                            dy_pinch = current_y - states["pinch_start_y"]

                            if abs(dy_pinch) >= states["brightness_dead_zone"]:
                                current_brightness = get_current_brightness()

                                if current_brightness is not None:
                                    brightness_change = int(
                                        (-dy_pinch) * states["brightness_sensitivity"]
                                    )

                                    new_brightness = current_brightness + brightness_change

                                    if set_current_brightness(new_brightness):
                                        states["pinch_start_x"] = current_x
                                        states["pinch_start_y"] = current_y

                        elif gesture_text == "DRAG":
                            states["last_pinch_type"] = None
                            states["left_click_frames"] = 0
                            states["right_click_frames"] = 0
                            states["double_click_frames"] = 0

                            states["move_mode_active"] = False
                            states["scroll_mode_active"] = False
                            states["pinch_mode_active"] = False

                            states["drag_release_frames"] = 0
                            states["drag_hold_frames"] += 1

                            hand_x, hand_y = gesture_data["drag_pos"]

                            cv2.circle(frame, (hand_x, hand_y), 10, (0, 255, 255), cv2.FILLED)

                            if (
                                not states["drag_active"]
                                and states["drag_hold_frames"] >= states["drag_start_threshold"]
                            ):
                                pyautogui.mouseDown(button="left")

                                states["drag_active"] = True
                                states["drag_mode_active"] = False

                            if states["drag_active"]:
                                if not states["drag_mode_active"]:
                                    states["drag_mode_active"] = True

                                    states["drag_start_hand_x"] = hand_x
                                    states["drag_start_hand_y"] = hand_y

                                    mouse_x, mouse_y = pyautogui.position()

                                    states["drag_start_mouse_x"] = mouse_x
                                    states["drag_start_mouse_y"] = mouse_y

                                    states["prev_drag_mouse_x"] = mouse_x
                                    states["prev_drag_mouse_y"] = mouse_y

                                dx = hand_x - states["drag_start_hand_x"]
                                dy = hand_y - states["drag_start_hand_y"]

                                if abs(dx) < states["drag_dead_zone"]:
                                    dx = 0

                                if abs(dy) < states["drag_dead_zone"]:
                                    dy = 0

                                target_mouse_x = (
                                    states["drag_start_mouse_x"]
                                    + dx * states["drag_sensitivity_x"]
                                )

                                target_mouse_y = (
                                    states["drag_start_mouse_y"]
                                    + dy * states["drag_sensitivity_y"]
                                )

                                target_mouse_x = max(0, min(screen_width - 1, target_mouse_x))
                                target_mouse_y = max(0, min(screen_height - 1, target_mouse_y))

                                smooth_drag_x = (
                                    states["prev_drag_mouse_x"]
                                    + (target_mouse_x - states["prev_drag_mouse_x"])
                                    / states["drag_smoothing"]
                                )

                                smooth_drag_y = (
                                    states["prev_drag_mouse_y"]
                                    + (target_mouse_y - states["prev_drag_mouse_y"])
                                    / states["drag_smoothing"]
                                )

                                pyautogui.moveTo(int(smooth_drag_x), int(smooth_drag_y))

                                states["prev_drag_mouse_x"] = smooth_drag_x
                                states["prev_drag_mouse_y"] = smooth_drag_y

                        elif gesture_text == "SCROLL":
                            states["last_pinch_type"] = None
                            states["left_click_frames"] = 0
                            states["right_click_frames"] = 0
                            states["double_click_frames"] = 0

                            states["move_mode_active"] = False
                            states["pinch_mode_active"] = False

                            handle_drag_release()

                            current_x, current_y = gesture_data["scroll_pos"]

                            cv2.circle(frame, (current_x, current_y), 10, (0, 200, 255), cv2.FILLED)

                            if not states["scroll_mode_active"]:
                                states["scroll_mode_active"] = True
                                states["scroll_start_y"] = current_y

                            dy_scroll = current_y - states["scroll_start_y"]

                            if abs(dy_scroll) >= states["scroll_dead_zone"]:
                                scroll_amount = int(
                                    (-dy_scroll) * states["scroll_sensitivity"]
                                )

                                if scroll_amount != 0:
                                    pyautogui.scroll(scroll_amount)
                                    states["scroll_start_y"] = current_y

                        elif gesture_text == "DOUBLE CLICK":
                            states["last_pinch_type"] = None

                            states["move_mode_active"] = False
                            states["scroll_mode_active"] = False
                            states["pinch_mode_active"] = False

                            handle_drag_release()

                            states["double_click_frames"] += 1
                            states["left_click_frames"] = 0
                            states["right_click_frames"] = 0

                            if (
                                states["click_cooldown"] == 0
                                and states["double_click_frames"] >= states["double_click_threshold"]
                            ):
                                pyautogui.doubleClick()

                                states["click_cooldown"] = states["cooldown_frames"]
                                states["double_click_frames"] = 0

                        elif gesture_text == "MOVE":
                            states["last_pinch_type"] = None

                            states["left_click_frames"] = 0
                            states["right_click_frames"] = 0
                            states["double_click_frames"] = 0

                            states["scroll_mode_active"] = False
                            states["pinch_mode_active"] = False

                            handle_drag_release()

                            x, y = gesture_data["move_pos"]

                            cv2.circle(frame, (x, y), 10, (255, 0, 0), cv2.FILLED)

                            if not states["move_mode_active"]:
                                states["move_mode_active"] = True

                                states["move_start_finger_x"] = x
                                states["move_start_finger_y"] = y

                                mouse_x, mouse_y = pyautogui.position()

                                states["move_start_mouse_x"] = mouse_x
                                states["move_start_mouse_y"] = mouse_y

                                states["prev_mouse_x"] = mouse_x
                                states["prev_mouse_y"] = mouse_y

                            dx = x - states["move_start_finger_x"]
                            dy = y - states["move_start_finger_y"]

                            if abs(dx) < states["dead_zone"]:
                                dx = 0
                            else:
                                dx = dx - states["dead_zone"] if dx > 0 else dx + states["dead_zone"]

                            if abs(dy) < states["dead_zone"]:
                                dy = 0
                            else:
                                dy = dy - states["dead_zone"] if dy > 0 else dy + states["dead_zone"]

                            target_mouse_x = (
                                states["move_start_mouse_x"]
                                + dx * states["move_sensitivity_x"]
                            )

                            target_mouse_y = (
                                states["move_start_mouse_y"]
                                + dy * states["move_sensitivity_y"]
                            )

                            target_mouse_x = max(0, min(screen_width - 1, target_mouse_x))
                            target_mouse_y = max(0, min(screen_height - 1, target_mouse_y))

                            smooth_mouse_x = (
                                states["prev_mouse_x"]
                                + (target_mouse_x - states["prev_mouse_x"])
                                / states["relative_smoothing"]
                            )

                            smooth_mouse_y = (
                                states["prev_mouse_y"]
                                + (target_mouse_y - states["prev_mouse_y"])
                                / states["relative_smoothing"]
                            )

                            current_mouse_x, current_mouse_y = pyautogui.position()

                            move_distance = (
                                (smooth_mouse_x - current_mouse_x) ** 2
                                + (smooth_mouse_y - current_mouse_y) ** 2
                            ) ** 0.5

                            if move_distance >= states["mouse_jitter_threshold"]:
                                pyautogui.moveTo(int(smooth_mouse_x), int(smooth_mouse_y))

                                states["prev_mouse_x"] = smooth_mouse_x
                                states["prev_mouse_y"] = smooth_mouse_y
                            else:
                                states["prev_mouse_x"] = current_mouse_x
                                states["prev_mouse_y"] = current_mouse_y

                        elif gesture_text == "LEFT CLICK":
                            states["last_pinch_type"] = None

                            states["move_mode_active"] = False
                            states["scroll_mode_active"] = False
                            states["pinch_mode_active"] = False

                            handle_drag_release()

                            states["left_click_frames"] += 1
                            states["right_click_frames"] = 0
                            states["double_click_frames"] = 0

                            if (
                                states["click_cooldown"] == 0
                                and states["left_click_frames"] >= states["click_threshold"]
                            ):
                                pyautogui.click(button="left")

                                states["click_cooldown"] = states["cooldown_frames"]
                                states["left_click_frames"] = 0

                        elif gesture_text == "RIGHT CLICK":
                            states["last_pinch_type"] = None

                            states["move_mode_active"] = False
                            states["scroll_mode_active"] = False
                            states["pinch_mode_active"] = False

                            handle_drag_release()

                            states["left_click_frames"] = 0
                            states["double_click_frames"] = 0

                            if states["right_click_ready"]:
                                states["right_click_frames"] += 1

                                if (
                                    states["click_cooldown"] == 0
                                    and states["right_click_frames"] >= states["click_threshold"]
                                ):
                                    pyautogui.click(button="right")

                                    states["click_cooldown"] = states["cooldown_frames"]
                                    states["right_click_frames"] = 0
                                    states["right_click_ready"] = False

                        else:
                            gesture_text = "Gesture not recognized"

                            states["left_click_frames"] = 0
                            states["right_click_frames"] = 0
                            states["double_click_frames"] = 0

                            states["move_mode_active"] = False
                            states["scroll_mode_active"] = False
                            states["pinch_mode_active"] = False
                            states["last_pinch_type"] = None

                            handle_drag_release()

                else:
                    gesture_text = "No hand detected"
                    self.reset_gesture_states(states, handle_drag_release)

                if states["click_cooldown"] > 0:
                    states["click_cooldown"] -= 1

                if gesture_text != states["last_gesture"]:
                    self.gesture_changed.emit(gesture_text)
                    states["last_gesture"] = gesture_text

                if self.camera_window_visible:
                    if not camera_window_open:
                        cv2.namedWindow(camera_window_name, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(
                            camera_window_name,
                            camera_window_width,
                            camera_window_height
                        )
                        if hasattr(cv2, "WND_PROP_TOPMOST"):
                            cv2.setWindowProperty(
                                camera_window_name,
                                cv2.WND_PROP_TOPMOST,
                                1
                            )
                        camera_window_open = True

                    cv2.imshow(camera_window_name, frame)
                    key = cv2.waitKey(1) & 0xFF
                else:
                    if camera_window_open:
                        cv2.destroyWindow(camera_window_name)
                        camera_window_open = False

                    key = cv2.waitKey(1) & 0xFF

                if key == ord("v"):
                    self.request_voice_command()

                if key == ord("q"):
                    self.running = False
                    break

        if states["drag_active"]:
            pyautogui.mouseUp(button="left")

        self.stop()

        cap.release()
        cv2.destroyAllWindows()

        voice_thread.join(timeout=1)
        tts_thread.join(timeout=1)
        wake_thread.join(timeout=1)
        command_thread.join(timeout=1)
