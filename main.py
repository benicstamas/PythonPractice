from machine import Pin
import time

# Common onboard LED pin on many ESP32 dev boards is GPIO2.
# If your board doesn't blink, we'll try a different pin.
LED_PIN = 2

led = Pin(LED_PIN, Pin.OUT)

while True:
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
``