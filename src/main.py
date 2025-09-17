# clock.py
# 4-Bit-Port (Pins 10..13) + Latch je Digit (Pins 6..9)
# TinyRTC (DS1307) Uhranzeige "hh:mm", zwei Taster (HH/MM) mit Auto-Repeat,
# I2C-Scanner und Hilfe.

from machine import Pin, I2C

try:
    from machine import SoftI2C  # Fallback, falls Hardware-I2C nicht verfügbar
except ImportError:
    SoftI2C = None
import time

# ----------------- 4-Bit-Port & Latch -----------------
# Datenpins: bit0->P10, bit1->P11, bit2->P12, bit3->P13
_DATA_PINS = [Pin(n, Pin.OUT) for n in (10, 11, 12, 13)]
# Latch-Pins je "digit": 0->6, 1->7, 2->8, 3->9
_LATCH_PINS = [Pin(n, Pin.OUT, value=0) for n in (6, 7, 8, 9)]
# Pulsbreite in Mikrosekunden (bei Bedarf anpassen)
_LATCH_WIDTH_US = 20

_value = 0  # zuletzt gesetzter 4-Bit-Wert (0..15)


def _write_data(v):
    """Schreibt die unteren 4 Bits von v auf die Datenpins und gibt v&0xF zurück."""
    v &= 0xF
    for i, p in enumerate(_DATA_PINS):
        p.value((v >> i) & 1)
    return v


def _pulse(pin):
    """Erzeugt einen kurzen High-Impuls auf dem angegebenen Pin."""
    pin.value(1)
    time.sleep_us(_LATCH_WIDTH_US)
    pin.value(0)


def set_port(value, digit=None):
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


def get_port():
    """Gibt den zuletzt gesetzten 4-Bit-Wert zurück (0..15)."""
    return _value


def set_wert(wert):
    """
    Zeigt eine ganze Zahl 0..9999 als vier Dezimalziffern an.
    Reihenfolge: digit0=Einer, 1=Zehner, 2=Hunderter, 3=Tausender.
    """
    if wert < 0:
        wert = 0
    if wert > 9999:
        wert = 9999
    for d in range(4):
        nibble = wert % 10
        set_port(nibble, d)  # Daten setzen + Digit d latchen
        wert //= 10


def show_hhmm(hh, mm):
    """Zeigt hh:mm auf 4 Ziffern (ohne Doppelpunktsteuerung)."""
    set_wert((int(hh) % 24) * 100 + (int(mm) % 60))


# ----------------- DS1307 TinyRTC -----------------
class DS1307:
    """
    Minimaler DS1307-Treiber (TinyRTC):
    - Startet die Uhr (CH-Bit löschen)
    - Liest/schreibt Zeit im 24h-Format
    """

    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        # CH-Bit (Clock Halt) löschen, falls gesetzt
        sec = self._read(0)
        if sec & 0x80:
            self._write(0, sec & 0x7F)

    @staticmethod
    def _bcd2dec(b):
        return (b >> 4) * 10 + (b & 0x0F)

    @staticmethod
    def _dec2bcd(d):
        return ((d // 10) << 4) | (d % 10)

    def _read(self, reg):
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def _write(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val]))

    def _decode_hours(self, hr):
        # 12h oder 24h robust decodieren
        if hr & 0x40:  # 12h
            h = self._bcd2dec(hr & 0x1F)
            if hr & 0x20:  # PM
                h = (h % 12) + 12
            else:
                h = h % 12
            return h
        # 24h
        return self._bcd2dec(hr & 0x3F)

    def get_time(self):
        # liest sec, min, hour
        data = self.i2c.readfrom_mem(self.addr, 0, 3)
        sec = self._bcd2dec(data[0] & 0x7F)
        minute = self._bcd2dec(data[1] & 0x7F)
        hour = self._decode_hours(data[2])
        return (hour, minute, sec)

    def set_time(self, hour, minute, sec=0):
        # auf 24h schreiben, Sekunden CH=0
        hour = int(hour) % 24
        minute = int(minute) % 60
        sec = int(sec) % 60
        self._write(0, self._dec2bcd(sec) & 0x7F)  # CH=0
        self._write(1, self._dec2bcd(minute) & 0x7F)
        self._write(2, self._dec2bcd(hour))  # 24h (bit6=0)


# Globale I2C/RTC-Instanzen
_I2C = None
_RTC = None


def _make_i2c(i2c_id, scl_pin, sda_pin, freq):
    """Erzeuge Hardware-I2C, fallback auf SoftI2C falls nötig."""
    try:
        return I2C(i2c_id, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
    except Exception:
        if SoftI2C is None:
            raise
        return SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)


def rtc_init(scl_pin=3, sda_pin=2, freq=100_000, i2c_id=1):
    """
    Initialisiert I2C & DS1307.
    Beispiel (RP2040/Pico): rtc_init(scl_pin=5, sda_pin=4)
    Beispiel (ESP32):       rtc_init(scl_pin=22, sda_pin=21)
    """
    global _I2C, _RTC
    _I2C = _make_i2c(i2c_id, scl_pin, sda_pin, freq)
    _RTC = DS1307(_I2C)
    return True


def rtc_get():
    """Gibt (hh, mm) zurück."""
    if _RTC is None:
        raise RuntimeError("RTC nicht initialisiert. rtc_init(...) zuerst aufrufen.")
    h, m, _ = _RTC.get_time()
    return (h, m)


def rtc_set(hh, mm):
    """Setzt (hh:mm); Sekunden werden auf 0 gesetzt. Kein Übertrag zwischen Feldern."""
    if _RTC is None:
        raise RuntimeError("RTC nicht initialisiert. rtc_init(...) zuerst aufrufen.")
    _RTC.set_time(int(hh) % 24, int(mm) % 60, 0)


# --------- I2C-Scanner ----------
def scan_i2c(scl_pin=3, sda_pin=2, freq=100_000, i2c_id=1, verbose=True):
    """
    Scannt den I2C-Bus und gibt eine sortierte Liste gefundener Adressen zurück.
    - Nutzt vorhandenen Bus (_I2C), falls initialisiert.
    - Andernfalls temporären Bus mit scl_pin/sda_pin erstellen.
    """
    # I2C-Instanz wählen/erzeugen
    if _I2C is not None and scl_pin is None and sda_pin is None:
        i2c = _I2C
    elif scl_pin is not None and sda_pin is not None:
        i2c = _make_i2c(i2c_id, scl_pin, sda_pin, freq)
    else:
        raise RuntimeError(
            "Kein I2C vorhanden. rtc_init(...) aufrufen oder scl_pin & sda_pin angeben."
        )

    addrs = sorted(i2c.scan())  # list[int]

    if verbose:
        if not addrs:
            print("I2C: keine Geräte gefunden.")
        else:
            print("I2C: gefunden:", ", ".join("0x{:02X}".format(a) for a in addrs))
            hints = []
            for a in addrs:
                if a == 0x68:
                    hints.append("0x68: DS1307/DS3231 (TinyRTC)")
                elif 0x50 <= a <= 0x57:
                    hints.append("0x%02X: AT24Cxx EEPROM" % a)
                elif a in (0x3C, 0x3D):
                    hints.append(f"0x{a:02X}: SSD1306 OLED")
                elif 0x20 <= a <= 0x27:
                    hints.append("0x%02X: PCF8574 I/O-Expander" % a)
                elif 0x38 <= a <= 0x3F:
                    hints.append("0x%02X: PCF8574A I/O-Expander" % a)
                elif a in (0x76, 0x77):
                    hints.append(f"0x{a:02X}: BME280")
            if hints:
                print("Hinweise:")
                for h in hints:
                    print("  -", h)
    return addrs


# ----------------- Taster mit Auto-Repeat -----------------
class _Button:
    def __init__(self, pin_no, pull_up=True, long_ms=600, rpt_ms=200):
        # aktiv-low (interner Pull-Up)
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_UP if pull_up else None)
        self.long_ms = long_ms
        self.rpt_ms = rpt_ms
        self._pressed = False
        self._t0 = 0
        self._next = 0

    def _is_down(self):
        return self.pin.value() == 0

    def process(self, now_ms, on_click, on_repeat):
        """
        Debounce/State-Maschine:
        - kurzer Klick => on_click()
        - lang gehalten => on_repeat() alle rpt_ms
        """
        down = self._is_down()
        if down and not self._pressed:
            # edge: pressed
            self._pressed = True
            self._t0 = now_ms
            self._next = now_ms + self.long_ms
        elif not down and self._pressed:
            # edge: released
            self._pressed = False
            if now_ms - self._t0 < self.long_ms:
                on_click()
        elif down and self._pressed:
            # held
            if now_ms >= self._next:
                on_repeat()
                self._next += self.rpt_ms


# ----------------- Clock-Loop -----------------
def clock_run(
    btn_hh_pin=26,
    btn_mm_pin=27,
    scl_pin=3,
    sda_pin=2,
    long_press_ms=600,
    repeat_ms=200,
    refresh_ms=100,
):
    """
    Startet die Uhr:
      - I2C/RTC initialisieren (scl_pin/sda_pin)
      - Zwei Taster (aktiv-low, interner Pull-Up) für HH & MM:
         * kurz drücken: +1
         * lang halten: nach ~long_press_ms alle repeat_ms weiter hochzählen
      - Anzeige hh:mm (kein Übertrag von Minuten auf Stunden).
    Läuft in einer Endlosschleife.
    """
    rtc_init(scl_pin, sda_pin)
    btn_hh = _Button(btn_hh_pin, long_ms=long_press_ms, rpt_ms=repeat_ms)
    btn_mm = _Button(btn_mm_pin, long_ms=long_press_ms, rpt_ms=repeat_ms)

    # Startanzeige
    hh, mm = rtc_get()
    show_hhmm(hh, mm)

    last_draw = -1
    while True:
        now = time.ticks_ms()

        def inc_h():
            nonlocal hh, mm
            hh = (hh + 1) % 24
            rtc_set(hh, mm)  # Sekunden = 0
            show_hhmm(hh, mm)

        def inc_m():
            nonlocal hh, mm
            mm = (mm + 1) % 60  # kein Übertrag auf Stunden
            rtc_set(hh, mm)
            show_hhmm(hh, mm)

        # Buttons verarbeiten
        btn_hh.process(now, on_click=inc_h, on_repeat=inc_h)
        btn_mm.process(now, on_click=inc_m, on_repeat=inc_m)

        # Zeit regelmäßig aus der RTC holen & anzeigen (falls extern geändert)
        if last_draw < 0 or time.ticks_diff(now, last_draw) >= refresh_ms:
            thh, tmm = rtc_get()
            if thh != hh or tmm != mm:
                hh, mm = thh, tmm
                show_hhmm(hh, mm)
            last_draw = now

        time.sleep_ms(20)


# ----------------- Hilfe -----------------
def help():
    print(
        "clock.py – 4-Bit-Port + TinyRTC (DS1307)\n"
        "Funktionen:\n"
        "  set_port(value[, digit]) -> int  : 4-Bit ausgeben, optional Digit 0..3 latchen (Pins 6..9).\n"
        "  get_port() -> int                 : letzten 4-Bit-Wert lesen.\n"
        "  set_wert(wert)                    : Zahl 0..9999 als vier Ziffern ausgeben (digit0=Einer .. digit3=Tausender).\n"
        "  show_hhmm(hh, mm)                 : Anzeige hh:mm (4 Ziffern).\n"
        "  rtc_init(scl_pin, sda_pin[, freq, i2c_id]) : I2C+DS1307 initialisieren.\n"
        "  rtc_get() -> (hh, mm)             : Uhrzeit aus RTC lesen.\n"
        "  rtc_set(hh, mm)                   : Uhrzeit setzen (Sekunden=0). Kein Übertrag Minuten->Stunden.\n"
        "  scan_i2c([scl_pin, sda_pin, freq, i2c_id, verbose]) -> list[int] : I2C-Bus scannen.\n"
        "  clock_run(btn_hh_pin, btn_mm_pin, scl_pin, sda_pin[, long_press_ms, repeat_ms, refresh_ms]) : Endlosschleife.\n"
        "Pins:\n"
        "  Daten: 10,11,12,13; Latch: 6,7,8,9. Latchpuls _LATCH_WIDTH_US (µs) anpassbar.\n"
        "Hinweis: TinyRTC/DS1307 hat oft 5V-Pullups auf I2C – bei 3,3V-Controllern Level-Shifter verwenden!\n"
    )


rtc_init()
clock_run()
