import urllib.urequest
import network
import time

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

def test(ssid, password):
    wlan.connect(ssid, password)
    while not wlan.isconnected() and wlan.status() >= 0:
        print("Waiting to connect to ", ssid)
        time.sleep(1)
    print("Connected")
    print(wlan.ifconfig())
    wlan.disconnect()

test('amberdown', 'candleandthestar')
test('marvin', 'marvin1234')
