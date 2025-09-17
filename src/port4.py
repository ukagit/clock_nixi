# Datei: port4.py
# 4-Bit-Port (Pins 10..13) + Latch pro Digit (Pins 6..9)
from machine import Pin
import time

# Datenpins: bit0->P10, bit1->P11, bit2->P12, bit3->P13
_DATA_PINS = [Pin(n, Pin.OUT) for n in (10, 11, 12, 13)]

# Latch-Pins je "digit": 0->6, 1->7, 2->8, 3->9
_LATCH_PINS = [Pin(n, Pin.OUT, value=0) for n in (6, 7, 8, 9)]

# Pulsbreite in Mikrosekunden (bei Bedarf anpassen)
_LATCH_WIDTH_US = 20

_value = 0  # zuletzt gesetzter 4-Bit-Wert (0..15)


def _write_data(v: int) -> int:
    """Schreibt die unteren 4 Bits von v auf die Datenpins und gibt v&0xF zurück."""
    v &= 0xF
    for i, p in enumerate(_DATA_PINS):
        p.value((v >> i) & 1)
    return v


def _pulse(pin: Pin) -> None:
    """Erzeugt einen kurzen High-Impuls auf dem angegebenen Pin."""
    pin.value(1)
    time.sleep_us(_LATCH_WIDTH_US)
    pin.value(0)


def set_port(value: int, digit: int | None = None) -> int:
    """
    Schreibt value (0..15) auf Pins 10..13.
    Optional: digit (0..3) -> Latch-Impuls auf zugehörigem Pin (6..9).
    Rückgabe: tatsächlich gesetzter 4-Bit-Wert (0..15).
    """
    global _value
    _value = _write_data(value)
    if digit is not None:
        if not (0 <= digit < len(_LATCH_PINS)):
            raise ValueError("digit außerhalb des erlaubten Bereichs")
        _pulse(_LATCH_PINS[digit])
    return _value


def get_port() -> int:
    """Gibt den zuletzt gesetzten 4-Bit-Wert zurück (0..15)."""
    return _value


def set_wert(wert: int) -> None:
    """
    Gibt eine ganze Zahl (0..9999) als vier Dezimalziffern aus.
    Reihenfolge: digit 0 = Einer, 1 = Zehner, 2 = Hunderter, 3 = Tausender.
    Führende Nullen werden angezeigt.
    """
    if wert < 0:
        wert = 0
    if wert > 9999:
        wert = 9999

    # Jede Ziffer (BCD) nacheinander ausgeben und latchen
    for d in range(4):
        nibble = wert % 10  # BCD 0..9
        set_port(nibble, d)  # Daten setzen + Digit d latchen
        wert //= 10


def help() -> None:
    """Listet die verfügbaren Funktionen und Pins auf."""
    text = (
        "port4 – 4-Bit-Port auf Pins 10..13 mit Latch auf 6..9\n"
        "Funktionen:\n"
        "  set_port(value[, digit]) -> int  : schreibt value (0..15); optional digit 0..3 latcht.\n"
        "  get_port() -> int                 : gibt zuletzt gesetzten 4-Bit-Wert zurück.\n"
        "  set_wert(wert)                    : gibt Ganzzahl 0..9999 als 4 Ziffern (digit0=Einer .. digit3=Tausender) aus.\n"
        "Konstanten/Anpassung:\n"
        "  Datenpins: 10,11,12,13; Latchpins: 6,7,8,9; Pulsbreite: _LATCH_WIDTH_US (µs)\n"
        "  Bei anderem Pin-Layout einfach _DATA_PINS/_LATCH_PINS anpassen."
    )
    print(text)

