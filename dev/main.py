from machine import I2C, Pin, Timer
import network
import time
import wifi_utils
import config

from oled_lib import OledDisplay
from gyros_lib import init_mpu6050
import gps_lib

# Hardwarové piny podle schématu (UART0 inicializuje gps_lib)
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5
BUTTON_PIN = 17

# Časové intervaly (ms)
WIFI_CHECK_MS = 5000
IMU_UPDATE_MS = 20
DISPLAY_UPDATE_MS = 150
GPS_TIMEOUT_MS = 3000
DEBOUNCE_MS = 250

is_wifi_connected = False
blink_state = True


def main():
    global is_wifi_connected, blink_state

    i2c = I2C(0, sda=Pin(I2C_SDA_PIN), scl=Pin(I2C_SCL_PIN), freq=100_000)
    display = OledDisplay(i2c)
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

    imu = init_mpu6050(i2c)
    if imu is not None:
        display.draw_message("Kalibrace IMU...")
        imu.calibrate(samples=60, delay_ms=10)

    display.clear_all()
    display.draw_header_line()
    display.draw_gps_icon(False)
    display.draw_wifi_icon(4, visible=True)
    display.show()

    def blink_callback(timer):
        global blink_state
        if not is_wifi_connected:
            blink_state = not blink_state
            display.draw_wifi_icon(4, visible=blink_state)
            display.show()

    blink_timer = Timer()
    blink_timer.init(period=750, mode=Timer.PERIODIC, callback=blink_callback)

    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    display_mode = 0
    last_button_state = 1
    last_button_time = 0

    last_wifi_check = time.ticks_add(time.ticks_ms(), -WIFI_CHECK_MS)
    last_imu_update = time.ticks_ms()
    last_display_update = time.ticks_ms()
    last_imu_retry = time.ticks_ms()
    imu_data = None

    print("System bezi (stisknete GP17 pro prepnuti obrazovky)...")

    try:
        while True:
            now = time.ticks_ms()

            # 1. Obsluha tlačítka na GP17
            current_button = button.value()
            if current_button == 0 and last_button_state == 1:
                if time.ticks_diff(now, last_button_time) > DEBOUNCE_MS:
                    last_button_time = now
                    display_mode = 1 - display_mode
                    display.clear_body()
                    display.show()
            last_button_state = current_button

            # 2. Průběžné čtení NMEA dat přes gps_lib
            gps_lib.update()

            # 3. Pokus o znovupřipojení MPU6050, pokud vypadl
            if imu is None and time.ticks_diff(now, last_imu_retry) >= 2000:
                last_imu_retry = now
                imu = init_mpu6050(i2c)
                if imu is not None:
                    imu.calibrate(samples=40, delay_ms=5)

            # 4. Čtení MPU6050
            if imu is not None and time.ticks_diff(now, last_imu_update) >= IMU_UPDATE_MS:
                last_imu_update = now
                try:
                    imu_data = imu.read()
                except Exception as e:
                    print("Chyba cteni MPU6050:", e)
                    imu = None
                    imu_data = None

            # 5. Kontrola Wi-Fi každých 5 sekund
            if time.ticks_diff(now, last_wifi_check) >= WIFI_CHECK_MS:
                last_wifi_check = now
                if not wifi.isconnected():
                    is_wifi_connected = False
                    try:
                        wifi_utils.connect(wifi, config.SSID, config.PSWD)
                    except Exception as e:
                        print("Chyba Wi-Fi:", e)

                if wifi.isconnected():
                    is_wifi_connected = True
                    bars = display.rssi_to_bars(wifi.status("rssi"))
                    display.draw_wifi_icon(bars, visible=True)
                else:
                    is_wifi_connected = False

            # 6. Aktualizace výpočtů navigace a vykreslení displeje
            if time.ticks_diff(now, last_display_update) >= DISPLAY_UPDATE_MS:
                last_display_update = now

                gps_data = gps_lib.get_data()
                last_upd = gps_data.get("last_update")
                gps_active = (
                    last_upd is not None
                    and time.ticks_diff(now, last_upd) < GPS_TIMEOUT_MS
                )
                gps_fixed = gps_lib.has_fix()

                # Průběžný výpočet směru pohybu a nadmořské výšky z GPS
                display.update_navigation(gps_data, gps_fixed)
                display.draw_gps_icon(gps_active)

                if display_mode == 0:
                    display.draw_sensor_data(gps_data, gps_active, gps_fixed, imu_data)
                else:
                    display.draw_motion_arrow_screen(gps_data, gps_fixed, imu_data)

                display.show()

            time.sleep_ms(5)

    except KeyboardInterrupt:
        print("\nProgram ukoncen uzivatelem.")
    finally:
        blink_timer.deinit()
        wifi_utils.disconnect(wifi)
        display.poweroff()


if __name__ == "__main__":
    main()
