import sys
import os
import subprocess
import datetime
import requests

import pyautogui
import screen_brightness_control as sbc


def get_current_brightness():
    try:
        value = sbc.get_brightness()

        if isinstance(value, list):
            return int(value[0])

        return int(value)

    except Exception as e:
        print("Brightness read error:", e)
        return None


def set_current_brightness(value):
    try:
        value = max(0, min(100, int(value)))
        sbc.set_brightness(value)
        return True

    except Exception as e:
        print("Brightness set error:", e)
        return False


def get_weather_varazdin():
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=46.3057"
            "&longitude=16.3366"
            "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
            "&timezone=Europe%2FBerlin"
        )

        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        current = data["current"]

        temperature = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind_speed = current["wind_speed_10m"]

        temp_text = round(temperature)
        humidity_text = round(humidity)
        wind_text = round(wind_speed)

        return (
            f"The current weather in Varaždin is {temp_text} degrees Celsius. "
            f"The humidity is {humidity_text} percent, "
            f"and the wind speed is {wind_text} kilometers per hour."
        )

    except Exception as e:
        return f"Weather error: {e}"


def open_calculator():
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["calc.exe"])
            return True

        return False

    except Exception as e:
        print("Calculator error:", e)
        return False


def open_notepad():
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["notepad.exe"])
            return True

        return False

    except Exception as e:
        print("Notepad error:", e)
        return False


def show_desktop():
    try:
        pyautogui.hotkey("win", "d")
        return True

    except Exception as e:
        print("Show desktop error:", e)
        return False


def take_screenshot():
    try:
        screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.join(
            screenshots_dir,
            f"screenshot_{timestamp}.png"
        )

        screenshot = pyautogui.screenshot()
        screenshot.save(file_path)

        return file_path

    except Exception as e:
        print("Screenshot error:", e)
        return None
