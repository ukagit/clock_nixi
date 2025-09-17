# Datei: port4.py
# 4-Bit-Port auf Pins 10..13 + Latch-Impulse auf Pins 6..9

from machine import Pin
import time

# Datenpins: bit0->P10, bit1->P11, bit2->P12, bit3->P13
_DATA_PINS = [Pin(n, Pin.OUT) for n in (10, 11, 12, 13)]

# Latch-Pins je "digit": 0->6, 1->7, 2->8, 3->9
# Falls du nur 6..8 zur Verfügung hast: LATCH_PINS = (6, 7, 8) und digit 0..2
_LATCH_PINS = [Pin(n, Pin.OUT, value=0) for n in (6, 7, 8, 9)]

# Pulsbreite in Mikrosekunden (an Hardware anpassen)
_LATCH_WIDTH_US = 20

_value = 0  # zuletzt gesetzter 4-Bit-Wert (0..15)


def _write_data(v):
    """Schreibt die unteren 4 Bits von v auf die Datenpins."""
    v &= 0xF
    for i, p in enumerate(_DATA_PINS):
        p.value((v >> i) & 1)
    return v


def _pulse(pin):
    """Erzeugt einen kurzen High-Puls auf dem angegebenen Pin."""
    pin.value(1)
    time.sleep_us(_LATCH_WIDTH_US)
    pin.value(0)


def set_port(value, digit=None):
    """
    Schreibt value (0..15) auf Pins 10..13.
    Optional: digit (0..3) -> erzeugt Latch-Impuls auf zugehörigem Pin (6..9).
    Rückgabe: tatsächlich gesetzter 4-Bit-Wert.
    """
    global _value
    _value = _write_data(value)
    if digit is not None:
        if not (0 <= digit < len(_LATCH_PINS)):
            raise ValueError("digit außerhalb des erlaubten Bereichs")
        _pulse(_LATCH_PINS[digit])
    return _value


def get_port():
    """Gibt den zuletzt gesetzten 4-Bit-Wert zurück (0..15)."""
    return _value

