# Copilot Instructions for PythonPractice

## Project Overview
This workspace contains ESP32 MicroPython firmware for a ride-on vehicle controller and an AHT10 sensor driver. The project is embedded firmware-focused and does not include Meshtastic or desktop IoT messaging code.

## Dependencies & Setup
- Target runtime: MicroPython on ESP32.
- Required files: `main.py` and `aht10.py`.
- Use a MicroPython deployment tool such as `mpremote`, Thonny, or a similar uploader.
- No `pip install` dependencies are required in this repository for the firmware itself.

## Running / Deploying
- Copy `main.py` and `aht10.py` to the ESP32 filesystem.
- Run `main.py` on the device as the firmware entry point.
- Adjust GPIO pin assignments in `main.py` before deployment to match your wiring.
- Ensure the device supports `machine`, `Pin`, `PWM`, `ADC`, `I2C`, and `ubluetooth` on MicroPython.

## Code Patterns
- BLE Nordic UART service for remote control payloads.
- PWM + direction control for throttle and steering.
- Latched fault handling with power-cycle reset.
- ADC battery and current monitoring with threshold-based safety checks.
- AHT10 temperature/humidity sensor driver on I2C.
- Minimal runtime configuration; values are hardcoded in `main.py`.

## File Structure
- `main.py`: ESP32 MicroPython firmware with BLE, PWM motor control, telemetry, and safety logic.
- `aht10.py`: AHT10 sensor driver for MicroPython.
- `readme`: Project notes and documentation.

## Development Notes
- Ignore any Meshtastic-related instructions or code; it is out of scope for this workspace.
- The firmware is self-contained and intended for embedded deployment rather than desktop execution.
- Keep imports and filenames consistent for MicroPython compatibility.
</content>
<parameter name="filePath">c:\Users\tbenics\OneDrive - Itron\Desktop\PythonPractice\.github\copilot-instructions.md