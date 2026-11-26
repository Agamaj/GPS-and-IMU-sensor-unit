from machine import I2C, Pin, UART, Timer
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

# GPS icon position (nalevo od ikony Wi-Fi)
GPS_X = ICON_X - 27       # x = 87
GPS_Y = 2                 # y = 2

# Globální proměnné pro řízení blikání z časovače
is_wifi_connected = False
blink_state = True


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


def draw_wifi_icon(oled, bars, visible=True):

    oled.fill_rect(ICON_X - 1, ICON_Y, 16, 12, 0)

    if not visible or bars <= 0:
        return

    cx = ICON_X + 6
    y = ICON_Y

    if bars >= 1:
        oled.fill_rect(cx, y + 9, 2, 2, 1)

    if bars >= 2:
        oled.hline(cx - 1, y + 6, 4, 1)
        oled.pixel(cx - 2, y + 7, 1)
        oled.pixel(cx + 3, y + 7, 1)

    if bars >= 3:
        oled.hline(cx - 2, y + 3, 6, 1)
        oled.pixel(cx - 3, y + 4, 1)
        oled.pixel(cx + 4, y + 4, 1)
        oled.pixel(cx - 4, y + 5, 1)
        oled.pixel(cx + 5, y + 5, 1)

    if bars >= 4:
        oled.hline(cx - 2, y, 6, 1)
        oled.hline(cx - 4, y + 1, 2, 1)
        oled.hline(cx + 4, y + 1, 2, 1)
        oled.pixel(cx - 5, y + 2, 1)
        oled.pixel(cx + 6, y + 2, 1)
        oled.pixel(cx - 6, y + 3, 1)
        oled.pixel(cx + 7, y + 3, 1)


def draw_gps_icon(oled, connected):

    oled.fill_rect(GPS_X - 3, 0, 28, 12, 0)

    if connected:
        oled.text("GPS", GPS_X, GPS_Y, 1)


def check_gps_active(uart):

    if uart.any():
        data = uart.read()
        if data and (b"$GP" in data or b"$GN" in data):
            return True
    return False


def main():
    global is_wifi_connected, blink_state

    i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100_000)
    oled = SH1106_I2C(i2c)
    gps_uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

    # Úvodní vykreslení
    oled.fill(0)
    draw_gps_icon(oled, False)
    draw_wifi_icon(oled, 4, visible=True)
    oled.show()

    # Callback pro časovač – spustí se každou 1 sekundu na pozadí
    def blink_callback(timer):
        global blink_state
        if not is_wifi_connected:
            blink_state = not blink_state
            draw_wifi_icon(oled, 4, visible=blink_state)
            oled.show()

    blink_timer = Timer()
    blink_timer.init(period=750, mode=Timer.PERIODIC, callback=blink_callback)

    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    print("Spoustim sledovani Wi-Fi a GPS (Ctrl+C pro ukonceni)...")

    try:
        while True:
            # 1. Kontrola GPS
            gps_ok = check_gps_active(gps_uart)
            draw_gps_icon(oled, gps_ok)
            print("GPS aktivni:", gps_ok)

            # 2. Kontrola Wi-Fi
            if not wifi.isconnected():
                is_wifi_connected = False
                print("Wi-Fi odpojeno. Pokousim se pripojit...")
                oled.show()

                # I během tohoto blokujícího volání nyní časovač plynule bliká ikonou
                try:
                    wifi_utils.connect(wifi, config.SSID, config.PSWD)
                except Exception as e:
                    print("Chyba pri pripojovani:", e)

            if wifi.isconnected():
                is_wifi_connected = True
                rssi = wifi.status("rssi")
                bars = rssi_to_bars(rssi)
                print(f"Pripojeno | RSSI: {rssi} dBm | Carky: {bars}/4")

                draw_wifi_icon(oled, bars, visible=True)
                oled.show()
            else:
                is_wifi_connected = False
                print("Bez signalu / nepripojeno")
                oled.fill_rect(0, 32, 128, 32, 0)
                oled.text("Stav: Bez sig.", 0, 34)
                oled.show()

            # Čekání 5 sekund do další kontroly
            time.sleep(5)

    except KeyboardInterrupt:
        print("\nProgram ukoncen uzivatelem.")
    finally:
        # Zastavení časovače před vypnutím displeje
        blink_timer.deinit()
        wifi_utils.disconnect(wifi)
        oled.fill(0)
        oled.show()
        oled.poweroff()


if __name__ == "__main__":
    main()
