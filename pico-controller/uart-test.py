from machine import UART, Pin
import time

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))
uart.write("hi from pico\n")
time.sleep(1)

while True:
    line = uart.readline()
    if not line:
        time.sleep(0.01)
    else:
        print("Received line:", line)
