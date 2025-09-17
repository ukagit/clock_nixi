# MicroPython I2C-Scanner für RP2040 (rp2)
from machine import Pin, I2C
import time

# Passen Sie diese drei Werte an Ihr Wiring an:
I2C_ID = 1  # 0 oder 1 auf dem RP2040
SCL_PIN = 3  # z.B. GP1
SDA_PIN = 2  # z.B. GP0

i2c = I2C(I2C_ID, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN), freq=400000)
# Falls instabil, probieren Sie freq=100000


def scan_once():
    devices = i2c.scan()
    if not devices:
        print("Keine I2C-Geräte gefunden.")
    else:
        print("Gefundene I2C-Adressen:")
        for addr in devices:
            print(" - 0x{:02X} ({})".format(addr, addr))
    return devices


# einmal scannen:
scan_once()

# oder kontinuierlich alle 2 Sekunden:
# while True:
#     scan_once()
#     time.sleep(2)
