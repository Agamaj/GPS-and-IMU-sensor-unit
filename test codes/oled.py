from machine import I2C, Pin
from sh1106 import SH1106_I2C
import network
import time
import wifi_utils
import config

OLED_WIDTH = 128
OLED_HEIGHT = 64

# WiFi icon position (right top corner)
ICON_X = OLED_WIDTH - 14  # x = 114
ICON_Y = 0                # y = 0

def rssi_to_bars(rssi):

    if rssi is None:
        return 0
    rssi = round(rssi)
    
    if rssi >= -55:
        return 4
    elif rssi >= -67:
        return 3
    elif rssi >= -78:
        return 2
    else:
        return 1
    
def draw_wifi_icon(oled, bars):

    oled.fill_rect(ICON_X, ICON_Y, 14, 12, 0)

    cx = ICON_X + 6
    y = ICON_Y

    if bars >= 1 or bars == 0:
        oled.fill_rect(cx, y + 9, 2, 2, 1)

    if bars >= 2 or bars == 0:
        oled.hline(cx - 1, y + 6, 4, 1)
        oled.pixel(cx - 2, y + 7, 1)
        oled.pixel(cx + 3, y + 7, 1)

    if bars >= 3 or bars == 0:
        oled.hline(cx - 2, y + 3, 6, 1)
        oled.pixel(cx - 3, y + 4, 1)
        oled.pixel(cx + 4, y + 4, 1)
        oled.pixel(cx - 4, y + 5, 1)
        oled.pixel(cx + 5, y + 5, 1)

    if bars >= 4 or bars == 0:
        oled.hline(cx - 2, y, 6, 1)
        oled.hline(cx - 4, y + 1, 2, 1)
        oled.hline(cx + 4, y + 1, 2, 1)
        oled.pixel(cx - 5, y + 2, 1)
        oled.pixel(cx + 6, y + 2, 1)
        oled.pixel(cx - 6, y + 3, 1)
        oled.pixel(cx + 7, y + 3, 1)

    if bars == 0:
        oled.line(ICON_X, y, ICON_X + 11, y + 9, 0)
        oled.line(ICON_X, y + 1, ICON_X + 11, y + 10, 1)

def main():

    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)
    oled = SH1106_I2C(i2c)

    oled.fill(0)
    oled.text("Raspberry Pi", 0, 2)
    oled.text("Pico W", 0, 14)
    oled.hline(0, 26, 128, 1)
    oled.text("Pripojovani...", 0, 34)
    draw_wifi_icon(oled, 0)
    oled.show()

    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    print("Spoustim sledovani Wi-Fi (Ctrl+C pro ukonceni)...")

    try:
        while True:
            if not wifi.isconnected():
                print("Wi-Fi odpojeno. Pokousim se pripojit...")
                draw_wifi_icon(oled, 0)
                oled.fill_rect(0, 32, 128, 32, 0)
                oled.text("Stav: Odpojeno", 0, 34)
                oled.show()

                try:
                    wifi_utils.connect(wifi, config.SSID, config.PSWD)
                except Exception as e:
                    print("Chyba pri pripojovani:", e)

            if wifi.isconnected():
                rssi = wifi.status("rssi")
                bars = rssi_to_bars(rssi)
                print(f"Pripojeno | RSSI: {rssi} dBm | Carky: {bars}/4")

                oled.fill_rect(0, 32, 128, 32, 0)
                oled.text("Stav: OK", 0, 34)
                oled.text(f"Sig: {round(rssi)} dBm", 0, 48)

                draw_wifi_icon(oled, bars)
                oled.show()
            else:
                print("Bez signalu / nepripojeno")
                draw_wifi_icon(oled, 0)
                oled.fill_rect(0, 32, 128, 32, 0)
                oled.text("Stav: Bez sig.", 0, 34)
                oled.show()

            time.sleep(5)

    except KeyboardInterrupt:
        print("\nProgram ukoncen uzivatelem.")
    finally:
        wifi_utils.disconnect(wifi)
        oled.fill(0)
        oled.show()
        oled.poweroff()


if __name__ == "__main__":
    main()