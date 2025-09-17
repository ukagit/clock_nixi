# blink_onboard.py
# Speichere als main.py auf dem Board, resetten, fertig.

import time

try:
    from machine import Pin
except ImportError:
    Pin = None


def find_onboard_led():
    # Pyboard (STM32): eigene LED-Klasse
    try:
        import pyb

        return ("pyb", pyb.LED(1))  # LED(1) ist meist die grüne LED
    except Exception:
        pass

    # Universeller Alias "LED" (z. B. RP2040/Pico W, einige ESP32-Ports)
    if Pin:
        try:
            return ("pin", Pin("LED", Pin.OUT))
        except Exception:
            pass

        # Heuristik für gängige Dev-Boards: ESP32(2), RP2040(25), weitere Kandidaten
        for guess in (2, 25, 5, 16):
            try:
                return ("pin", Pin(guess, Pin.OUT))
            except Exception:
                pass

    raise RuntimeError("Onboard-LED nicht gefunden. Bitte Pin manuell angeben.")


kind, led = find_onboard_led()

state = 0
while True:
    if kind == "pyb":
        led.toggle()
    else:
        state ^= 1
        led.value(state)
    time.sleep(0.5)  # Blink-Intervall anpassen (Sekunden)
