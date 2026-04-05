import time
import struct
import bluetooth
from machine import Pin
from micropython import const


from machine import DAC, Pin
import time

# Use GPIO25 = DAC1
dac = DAC(Pin(25))

# Write a value between 0..255
# 0   -> 0 V
# 255 -> ~3.3 V

def set_speed(percent):
    percent = max(0, min(100, percent))
    dac_value = int(percent * 255 / 100)
    dac.write(dac_value)


# IRQ event numbers (MicroPython BLE peripheral)
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

LED_PIN = 2
led = Pin(LED_PIN, Pin.OUT)

# Nordic UART Service-like UUIDs (what you already have)
SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
RX_UUID      = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # Write from phone -> ESP32
TX_UUID      = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # Notify from ESP32 -> phone (unused for now)

RX_CHAR = (RX_UUID, bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE)
TX_CHAR = (TX_UUID, bluetooth.FLAG_NOTIFY)
SERVICE = (SERVICE_UUID, (RX_CHAR, TX_CHAR))


def adv_payload(name="RideOn"):
    payload = bytearray()

    def add(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type))
        payload.extend(value)

    add(0x01, b"\x06")          # flags: LE General Discoverable + BR/EDR not supported
    add(0x09, name.encode())    # complete local name
    return payload


class RideOnBLE:
    def __init__(self, ble, name="RideOn"):
        self._ble = ble
        self._ble.active(True)
        # Optional but useful later for higher traffic:
        # self._ble.config(rxbuf=256)

        self._ble.irq(self._irq)

        ((self._rx_handle, self._tx_handle),) = self._ble.gatts_register_services((SERVICE,))
        self._connections = set()

        self.throttle = 0
        self.steering = 0

        self._payload = adv_payload(name)
        self._advertise()

    def _advertise(self, interval_us=100000):
        self._ble.gap_advertise(None)
        time.sleep_ms(50)
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
        print("Advertising as:", "RideOn")
        led.on()
        time.sleep_ms(100)
        led.off()

    def is_connected(self):
        return len(self._connections) > 0

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, addr_type, addr = data
            self._connections.add(conn_handle)
            print("Connected:", conn_handle)
            led.on()

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            self._connections.discard(conn_handle)
            print("Disconnected:", conn_handle)
            led.off()
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self._rx_handle:
                rx = self._ble.gatts_read(self._rx_handle)

                # Expect exactly 2 bytes: int8 throttle, int8 steering
                if len(rx) < 2:
                    print("RX too short:", rx, "len=", len(rx))
                    return

                # Parse first 2 bytes as signed int8
                t, s = struct.unpack("bb", rx[:2])
                self.throttle = int(t)
                self.steering = int(s)

                # Print separately, as requested
                print("Throttle:", self.throttle, " Steering:", self.steering)

                # Optional: if you want to see raw too
                # print("Raw RX:", rx)
                set_speed(self.throttle)


ble = bluetooth.BLE()
dev = RideOnBLE(ble)

# No heartbeat loop. Just keep the script alive.
while True:
    time.sleep(1)