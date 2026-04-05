# main.py — ESP32 MicroPython BLE: advertise short name + GATT service (RX write, TX notify)
import time
import struct
import bluetooth
from machine import Pin
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

LED_PIN = 2
led = Pin(LED_PIN, Pin.OUT)

# --- Custom 128-bit UUIDs (Nordic-UART-like style) ---
SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
RX_UUID      = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # Write from phone -> ESP32
TX_UUID      = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # Notify from ESP32 -> phone

# GATT characteristics
RX_CHAR = (RX_UUID, bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE)
TX_CHAR = (TX_UUID, bluetooth.FLAG_NOTIFY)

SERVICE = (SERVICE_UUID, (RX_CHAR, TX_CHAR))

# Advertising payload: keep it SMALL (flags + name only)
def adv_payload(name="RideOn"):
    payload = bytearray()

    def add(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type))
        payload.extend(value)

    # Flags: LE General Discoverable + BR/EDR not supported
    add(0x01, b"\x06")
    # Complete local name
    add(0x09, name.encode())

    return payload


class RideOnBLE:
    def __init__(self, ble, name="RideOn"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        # Register service, get value handles
        ((self._rx_handle, self._tx_handle),) = self._ble.gatts_register_services((SERVICE,))

        self._connections = set()
        self._name = name
        self._payload = adv_payload(name)

        self._advertise()

    def _advertise(self, interval_us=100000):
        # Stop any ongoing advertising then restart.
        # This is helpful when reconnecting.
        self._ble.gap_advertise(None)
        time.sleep_ms(50)
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
        print("Advertising as:", self._name)

    def is_connected(self):
        return len(self._connections) > 0

def _irq(self, event, data):
    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle, addr_type, addr = data
        self._connections.add(conn_handle)
        print("Connected:", conn_handle)

    elif event == _IRQ_CENTRAL_DISCONNECT:
        conn_handle, addr_type, addr = data
        self._connections.discard(conn_handle)
        print("Disconnected:", conn_handle)
        self._advertise()

    elif event == _IRQ_GATTS_WRITE:
        conn_handle, value_handle = data
        if value_handle == self._rx_handle:
            rx = self._ble.gatts_read(self._rx_handle)
            print("RX bytes:", rx)

    def notify(self, data: bytes):
        # Send notify to all active connections
        for conn_handle in list(self._connections):
            try:
                self._ble.gatts_notify(conn_handle, self._tx_handle, data)
            except Exception:
                pass


# ---- Start BLE ----
ble = bluetooth.BLE()
dev = RideOnBLE(ble, name="RideOn")

counter = 0

while True:
    # LED behavior: slow blink when advertising, solid on when connected
    print("heartbeat", time.ticks_ms())
    if dev.is_connected():
        led.on()
        print("heartbeatConnected", time.ticks_ms())
    else:
        led.on()
        print("heartbeatsearching", time.ticks_ms())
        time.sleep(0.3)
        led.off()

    # Optional: send a notify once per second when connected
    if dev.is_connected():
        counter += 1
        dev.notify(("hello %d" % counter).encode())