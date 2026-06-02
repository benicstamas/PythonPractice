# main.py - RideOn ESP32 MicroPython firmware (PWM + safety + BLE)
#
# Features:
# - BLE RX: 2-byte signed control payload [throttle, steering]
# - PWM + direction bit for throttle and steering
# - Boot-time current sensor calibration with sanity check
# - Latched faults (reset only by power-cycle)
# - Telemetry notifications (max temp, vbat, current, fault flags)
#
# IMPORTANT:
# - Requires aht10.py present on the device (in the same directory as this file).
# - You MUST adjust GPIO pin assignments to your wiring.

import time
from machine import Pin, PWM, ADC, I2C
import ubluetooth
from struct import pack

# =========================
# GPIO CONFIG (EDIT ME)
# =========================

# PWM + direction bit
THR_PWM_PIN = 25
THR_DIR_PIN = 32
STR_PWM_PIN = 26
STR_DIR_PIN = 33

# ADC pins
VBAT_ADC_PIN = 34
CURR_ADC_PIN = 35

# AHT10: 5 sensors, each on its own I2C bus (EDIT ME)
# Use only safe ESP32 pins (avoid 0,2,4,5,12,15 where possible).
I2C_PINS = [
    (16, 17),  # (SCL, SDA)
    (18, 19),
    (21, 22),
    (23, 27),
    (14, 12),
]

# =========================
# SAFETY THRESHOLDS
# =========================
# TEMP_LIMIT_C    = 70.0
CURRENT_LIMIT_A = 40.0
UNDERVOLT_V     = 10.0
OVERVOLT_V      = 20.0

# =========================
# ADC / CALIBRATION
# =========================
ADC_REF = 3.3
ADC_MAX = 4095

# Battery divider ratio (Vbat = Vadc * VBAT_DIVIDER)
VBAT_DIVIDER = 25.0

# ACS754 scaling
DIVIDER_RATIO = 2.0          # 1:1 divider on ACS754 output -> multiply ADC voltage by 2 to get sensor voltage
ACS_GAIN_V_PER_A = 0.04      # 40 mV/A typical for ACS754-050B
ACS_ZERO_ADC_NOMINAL = 1.25  # expected ADC-side zero voltage (V) with divider
ACS_ZERO_TOL = 0.125         # ±10%

# =========================
# PWM
# =========================
PWM_FREQ = 20000
PWM_MAX  = 1023

# =========================
# BLE (Nordic UART)
# =========================
_UART_UUID = ubluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
_UART_TX   = ubluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')  # notify
_UART_RX   = ubluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')  # write

_IRQ_CENTRAL_CONNECT    = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE        = 3

_FLAG_NOTIFY            = 0x0010
_FLAG_WRITE             = 0x0008
_FLAG_WRITE_NO_RESPONSE = 0x0004

# =========================
# FAULT FLAGS (latched until power-cycle)
# =========================
FAULT_OVERTEMP    = 1 << 0
FAULT_OVERCURRENT = 1 << 1
FAULT_UNDERVOLT   = 1 << 2
FAULT_OVERVOLT    = 1 << 3
FAULT_CAL_INVALID = 1 << 4

# =========================
# TELEMETRY
# =========================
TELEMETRY_PERIOD_MS = 500

# =========================
# Hardware init
# =========================

thr_pwm = PWM(Pin(THR_PWM_PIN), freq=PWM_FREQ, duty=0)
thr_dir = Pin(THR_DIR_PIN, Pin.OUT)

str_pwm = PWM(Pin(STR_PWM_PIN), freq=PWM_FREQ, duty=0)
str_dir = Pin(STR_DIR_PIN, Pin.OUT)

adc_vbat = ADC(Pin(VBAT_ADC_PIN))
adc_vbat.atten(ADC.ATTN_11DB)

adc_curr = ADC(Pin(CURR_ADC_PIN))
adc_curr.atten(ADC.ATTN_11DB)

# AHT10 sensors
# from aht10 import AHT10

# i2c_list = []
# sensors = []
# for idx, (scl, sda) in enumerate(I2C_PINS):
#    i2c = I2C(idx, scl=Pin(scl), sda=Pin(sda))
#   i2c_list.append(i2c)
#   sensors.append(AHT10(i2c))

# =========================
# Global state
# =========================

motors_enabled   = False
calibration_done = False
fault_latched    = False
fault_flags      = 0

# Calibrated sensor-side zero voltage
ACS_ZERO_V = 2.50

# BLE handles
_ble = ubluetooth.BLE()
_ble.active(True)
_ble.config(rxbuf=256)

_conn_handle = None
_tx_handle = None
_rx_handle = None
_connections = set()

# =========================
# Helpers
# =========================

def adc_to_v(raw):
    return (raw * ADC_REF) / ADC_MAX


def stop_motors():
    thr_pwm.duty(0)
    str_pwm.duty(0)


def emergency_stop(reason_bit):
    global motors_enabled, fault_latched, fault_flags
    stop_motors()
    motors_enabled = False
    fault_latched = True
    fault_flags |= reason_bit


def apply_axis(pwm, dir_pin, value):
    # value is int8 (-127..127)
    if not motors_enabled:
        pwm.duty(0)
        return

    if value > 0:
        dir_pin.on()
        duty = int((value / 127) * PWM_MAX)
    elif value < 0:
        dir_pin.off()
        duty = int((abs(value) / 127) * PWM_MAX)
    else:
        duty = 0

    pwm.duty(duty)


def apply_drive(throttle, steering):
    apply_axis(thr_pwm, thr_dir, throttle)
    apply_axis(str_pwm, str_dir, steering)


def read_vbat():
    raw = adc_vbat.read()
    v_adc = adc_to_v(raw)
    return v_adc * VBAT_DIVIDER


def read_current_A():
    raw = adc_curr.read()
    v_adc = adc_to_v(raw)
    v_sensor = v_adc * DIVIDER_RATIO
    return (v_sensor - ACS_ZERO_V) / ACS_GAIN_V_PER_A


#def read_max_temp_C():
#    temps = []
#    for s in sensors:
#        try:
#            temps.append(s.temperature)
#        except Exception:
#            # if a sensor read fails, treat as very hot -> immediate safe stop
#            temps.append(999.0)
#    return max(temps) if temps else 999.0


# =========================
# Boot-time calibration
# =========================

def calibrate_current_zero():
    """Calibrate ACS754 zero offset at boot.

    - Motors are forced OFF during calibration.
    - Waits a short settle delay.
    - Takes N samples and uses median.
    - Sanity-checks the ADC-side zero voltage.
    """
    global ACS_ZERO_V, calibration_done

    stop_motors()
    time.sleep_ms(200)  # settle time for rails + ADC

    samples = []
    N = 41
    for _ in range(N):
        raw = adc_curr.read()
        samples.append(adc_to_v(raw))
        time.sleep_ms(2)

    samples.sort()
    adc_zero = samples[N // 2]

    lo = ACS_ZERO_ADC_NOMINAL - ACS_ZERO_TOL
    hi = ACS_ZERO_ADC_NOMINAL + ACS_ZERO_TOL

    if not (lo <= adc_zero <= hi):
        emergency_stop(FAULT_CAL_INVALID)
        return

    ACS_ZERO_V = adc_zero * DIVIDER_RATIO
    calibration_done = True


# =========================
# Safety checks (latched)
# =========================

def safety_check():
    if fault_latched:
        return

    tmax = read_max_temp_C()
    iabs = abs(read_current_A())
    vbat = read_vbat()

    if tmax >= TEMP_LIMIT_C:
        emergency_stop(FAULT_OVERTEMP)
    elif iabs >= CURRENT_LIMIT_A:
        emergency_stop(FAULT_OVERCURRENT)
    elif vbat <= UNDERVOLT_V:
        emergency_stop(FAULT_UNDERVOLT)
    elif vbat >= OVERVOLT_V:
        emergency_stop(FAULT_OVERVOLT)


# =========================
# BLE
# =========================

def _advertise():
    # Keep advertising payload small to avoid OSError -18.
    # Flags + Complete Local Name
    name = b'RideOn'
    adv = bytearray(b'\x02\x01\x06') + bytearray((len(name) + 1, 0x09)) + name
    _ble.gap_advertise(100000, adv)


def _irq(event, data):
    global _conn_handle

    if event == _IRQ_CENTRAL_CONNECT:
        conn_handle, _, _ = data
        _connections.add(conn_handle)
        _conn_handle = conn_handle

    elif event == _IRQ_CENTRAL_DISCONNECT:
        conn_handle, _, _ = data
        _connections.discard(conn_handle)
        _conn_handle = None
        # Ensure safe stop on disconnect
        stop_motors()
        _advertise()

    elif event == _IRQ_GATTS_WRITE:
        conn_handle, value_handle = data
        if value_handle == _rx_handle:
            payload = _ble.gatts_read(_rx_handle)
            if len(payload) >= 2:
                # Two signed int8 bytes: [throttle, steering]
                thr = int.from_bytes(payload[0:1], 'big', signed=True)
                st  = int.from_bytes(payload[1:2], 'big', signed=True)

                # Apply only if allowed
                if motors_enabled and (not fault_latched):
                    apply_drive(thr, st)
                else:
                    stop_motors()


def ble_init():
    global _tx_handle, _rx_handle

    _ble.irq(_irq)

    uart_tx = (_UART_TX, _FLAG_NOTIFY)
    uart_rx = (_UART_RX, _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE)
    uart_service = (_UART_UUID, (uart_tx, uart_rx))

    (( _tx_handle, _rx_handle ),) = _ble.gatts_register_services((uart_service,))

    _advertise()


# =========================
# Telemetry
# =========================

def build_telemetry():
    tmax = read_max_temp_C()
    vbat = read_vbat()
    iabs = abs(read_current_A())

    # Packet:
    # int16 temp_cC, uint16 vbat_cV, uint16 curr_cA, uint8 flags
    temp_cC = int(tmax * 100)
    vbat_cV = int(vbat * 100)
    curr_cA = int(iabs * 100)

    return pack('>hHHB', temp_cC, vbat_cV, curr_cA, fault_flags & 0xFF)


def notify_telemetry():
    if not _connections:
        return

    pkt = build_telemetry()
    for ch in list(_connections):
        try:
            _ble.gatts_notify(ch, _tx_handle, pkt)
        except Exception:
            pass


# =========================
# MAIN
# =========================

def main():
    global motors_enabled

    stop_motors()
    ble_init()

    # Boot-time calibration gate
    calibrate_current_zero()

    # Motors only enabled if calibration ok and no faults
    motors_enabled = calibration_done and (not fault_latched)

    last_tx = time.ticks_ms()

    while True:
        safety_check()

        # Keep motors off if fault latched
        if fault_latched:
            stop_motors()

        if time.ticks_diff(time.ticks_ms(), last_tx) >= TELEMETRY_PERIOD_MS:
            notify_telemetry()
            last_tx = time.ticks_ms()

        time.sleep_ms(20)


main()
