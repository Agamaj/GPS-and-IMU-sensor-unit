from machine import I2C, Pin, UART, Timer
from sh1106 import SH1106_I2C
import network
import struct
import time
import wifi_utils
import config

OLED_WIDTH = 128
OLED_HEIGHT = 64

# Piny přesně podle schématu zapojení:
# I2C0: GP4 = SDA, GP5 = SCL (sdíleno pro OLED a MPU6050)
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5

# UART0: GP0 = TX (na RXD GPS), GP1 = RX (na TXD GPS)
UART_TX_PIN = 0
UART_RX_PIN = 1

# Pozice ikon v pravém horním rohu
ICON_X = OLED_WIDTH - 14  # x = 114
ICON_Y = 0                # y = 0
GPS_X = ICON_X - 27       # x = 87
GPS_Y = 2                 # y = 2
HEADER_LINE_Y = 13

# Intervaly obnovování (ms)
WIFI_CHECK_MS = 5000      # Kontrola Wi-Fi každých 5 s
DISPLAY_UPDATE_MS = 250   # Obnovení dat na OLED 4x za sekundu
GPS_TIMEOUT_MS = 3000     # Po 3 s bez dat zhasne ikona GPS

# Globální proměnné pro řízení blikání Wi-Fi z časovače
is_wifi_connected = False
blink_state = True


# ==============================================================================
# 1. TŘÍDA PRO MPU6050 (s podporou adres 0x68 i 0x69)
# ==============================================================================
class MPU6050:
    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address
        self.gyro_offset = [0.0, 0.0, 0.0]

        # Probuzení senzoru
        self.i2c.writeto_mem(self.address, 0x6B, b'\x00')
        time.sleep_ms(50)
        # Rozsah akcelerometru: +/- 2g
        self.i2c.writeto_mem(self.address, 0x1C, b'\x00')
        # Rozsah gyroskopu: +/- 250 deg/s
        self.i2c.writeto_mem(self.address, 0x1B, b'\x00')
        time.sleep_ms(50)

    def read_raw(self):
        data = self.i2c.readfrom_mem(self.address, 0x3B, 14)
        return struct.unpack(">hhhhhhh", data)

    def read(self):
        ax, ay, az, temp, gx, gy, gz = self.read_raw()
        return {
            "accel": {
                "x": ax / 16384 * 9.80665,
                "y": ay / 16384 * 9.80665,
                "z": az / 16384 * 9.80665
            },
            "gyro": {
                "x": gx / 131.0 - self.gyro_offset[0],
                "y": gy / 131.0 - self.gyro_offset[1],
                "z": gz / 131.0 - self.gyro_offset[2]
            }
        }

    def calibrate(self, samples=50, delay_ms=10):
        offsets = [0.0, 0.0, 0.0]
        for _ in range(samples):
            raw = self.read_raw()
            offsets[0] += raw[4] / 131.0
            offsets[1] += raw[5] / 131.0
            offsets[2] += raw[6] / 131.0
            time.sleep_ms(delay_ms)

        self.gyro_offset = [value / samples for value in offsets]
        return self.gyro_offset


def init_mpu6050(i2c):
    """Vyhledá MPU6050 na I2C sběrnici (adresa 0x68 nebo 0x69) a inicializuje ho."""
    devices = i2c.scan()
    print("Nalezena I2C zarizeni:", [hex(d) for d in devices])
    for addr in (0x68, 0x69):
        if addr in devices:
            try:
                sensor = MPU6050(i2c, address=addr)
                print(f"MPU6050 pripojen na adrese {hex(addr)}")
                return sensor
            except Exception as e:
                print(f"Chyba inicializace MPU6050 na {hex(addr)}:", e)
    return None


# ==============================================================================
# 2. GPS NMEA PARSER
# ==============================================================================
def create_gps_data():
    return {
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "fix_quality": None,
        "fix_mode": None,
        "status": None,
        "satellites": None,
        "satellites_used": [],
        "satellites_in_view": None,
        "hdop": None,
        "vdop": None,
        "pdop": None,
        "speed_knots": None,
        "speed_kmh": None,
        "course": None,
        "time": None,
        "date": None,
        "last_sentence": None,
        "last_update": None
    }


def to_float(value):
    try:
        return float(value) if value else None
    except ValueError:
        return None


def to_int(value):
    try:
        return int(value) if value else None
    except ValueError:
        return None


def convert_coordinate(value, direction):
    if not value or not direction:
        return None
    try:
        degrees = int(float(value) / 100)
        minutes = float(value) - degrees * 100
        decimal = degrees + minutes / 60
        if direction in ("S", "W"):
            decimal = -decimal
        return decimal
    except ValueError:
        return None


def format_nmea_time(raw_time):
    """Převede NMEA čas 'hhmmss.ss' na čitelný formát 'HH:MM:SS'."""
    if not raw_time or len(raw_time) < 6:
        return "--:--:--"
    return f"{raw_time[0:2]}:{raw_time[2:4]}:{raw_time[4:6]}"


def checksum_valid(sentence):
    if "*" not in sentence:
        return False
    try:
        data, checksum = sentence.split("*", 1)
        calculated = 0
        for char in data[1:]:
            calculated ^= ord(char)
        return calculated == int(checksum[:2], 16)
    except (ValueError, IndexError):
        return False


def parse_nmea(sentence, gps_data):
    sentence = sentence.strip()
    if not sentence.startswith("$") or not checksum_valid(sentence):
        return False

    data = sentence[1:sentence.index("*")]
    fields = data.split(",")
    sentence_type = fields[0][-3:]

    if sentence_type == "GGA":
        updates = {
            "time": fields[1],
            "latitude": convert_coordinate(fields[2], fields[3]),
            "longitude": convert_coordinate(fields[4], fields[5]),
            "fix_quality": to_int(fields[6]),
            "satellites": to_int(fields[7]),
            "hdop": to_float(fields[8]),
            "altitude": to_float(fields[9])
        }
    elif sentence_type == "RMC":
        speed_knots = to_float(fields[7])
        updates = {
            "time": fields[1],
            "status": fields[2],
            "latitude": convert_coordinate(fields[3], fields[4]),
            "longitude": convert_coordinate(fields[5], fields[6]),
            "speed_knots": speed_knots,
            "speed_kmh": (speed_knots * 1.852) if speed_knots is not None else None,
            "course": to_float(fields[8]),
            "date": fields[9]
        }
    elif sentence_type == "GLL":
        updates = {
            "latitude": convert_coordinate(fields[1], fields[2]),
            "longitude": convert_coordinate(fields[3], fields[4]),
            "time": fields[5],
            "status": fields[6]
        }
    elif sentence_type == "GSA":
        updates = {
            "fix_mode": to_int(fields[2]),
            "satellites_used": [value for value in fields[3:15] if value],
            "pdop": to_float(fields[15]),
            "hdop": to_float(fields[16]),
            "vdop": to_float(fields[17])
        }
    elif sentence_type == "GSV":
        updates = {
            "satellites_in_view": to_int(fields[3])
        }
    elif sentence_type == "VTG":
        updates = {
            "course": to_float(fields[1]),
            "speed_knots": to_float(fields[5]),
            "speed_kmh": to_float(fields[7])
        }
    else:
        return False

    for key, value in updates.items():
        if value is not None and value != "":
            gps_data[key] = value

    gps_data["last_sentence"] = sentence_type
    gps_data["last_update"] = time.ticks_ms()
    return True


# ==============================================================================
# 3. VYKRESLOVÁNÍ IKON A DAT NA OLED (bez překrývání)
# ==============================================================================
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


def draw_sensor_data(oled, gps_data, gps_active, imu_data):
    """
    Vykreslí data z GPS a MPU6050 do pevných nekonfliktních řádků (max 16 znaků/řádek):
      y = 16: GPS řádek 1 (šířka / UTC čas + počet satelitů)
      y = 26: GPS řádek 2 (délka / rychlost + stav příjmu)
      y = 37: dělící čára
      y = 41: Akcelerometr (X, Y, Z)
      y = 52: Gyroskop (X, Y, Z)
    """
    # Vymazání celé plochy pod horní stavovou lištou
    oled.fill_rect(0, HEADER_LINE_Y + 2, OLED_WIDTH, OLED_HEIGHT - (HEADER_LINE_Y + 2), 0)

    # --- SEKCE GPS (2 řádky po max. 16 znacích = 128 px) ---
    lat = gps_data["latitude"]
    lon = gps_data["longitude"]
    sats_used = gps_data["satellites"] if gps_data["satellites"] is not None else 0
    sats_view = gps_data["satellites_in_view"] if gps_data["satellites_in_view"] is not None else 0
    spd = gps_data["speed_kmh"] if gps_data["speed_kmh"] is not None else 0.0
    utc_str = format_nmea_time(gps_data["time"])

    if not gps_active:
        oled.text("GPS: Odpojeno", 0, 16)
        oled.text("Cekam na UART...", 0, 26)
    elif lat is not None and lon is not None:
        # Máme platný GPS fix -> zobrazíme souřadnice, satelity a rychlost
        # Formát: "La:49.1951 S:06" (15 znaků = 120 px, žádné překrytí)
        oled.text(f"La:{lat:7.4f} S:{sats_used:02d}", 0, 16)
        # Formát: "Lo:16.6068 000km" (16 znaků = 128 px)
        oled.text(f"Lo:{lon:7.4f} {spd:3.0f}km", 0, 26)
    else:
        # GPS komunikuje, ale ještě nemá fix -> vypíšeme UTC čas, satelity a typ věty
        # Formát: "UTC 12:34:56 GGA" (16 znaků = 128 px)
        msg = gps_data["last_sentence"] or "---"
        oled.text(f"UTC {utc_str} {msg}", 0, 16)
        # Formát: "Sat:0/08 NoFix" (14 znaků = 112 px)
        oled.text(f"Sat:{sats_used}/{sats_view:02d} NoFix", 0, 26)

    # Středová dělící čára mezi GPS a IMU
    oled.hline(0, 37, OLED_WIDTH, 1)

    # --- SEKCE MPU6050 (2 řádky po max. 16 znacích) ---
    if imu_data is not None:
        ax = imu_data["accel"]["x"]
        ay = imu_data["accel"]["y"]
        az = imu_data["accel"]["z"]
        gx = imu_data["gyro"]["x"]
        gy = imu_data["gyro"]["y"]
        gz = imu_data["gyro"]["z"]

        # Formát: "A: 0.1 -0.2  9.8" (16 znaků = 128 px)
        oled.text(f"A:{ax:4.1f} {ay:4.1f} {az:4.1f}", 0, 41)
        # Formát: "G:   0   -1    2" (16 znaků = 128 px)
        oled.text(f"G:{gx:4.0f} {gy:4.0f} {gz:4.0f}", 0, 52)
    else:
        oled.text("IMU: Odpojeno", 0, 41)
        oled.text("Hledam I2C...", 0, 52)


# ==============================================================================
# 4. HLAVNÍ SMYČKA PROGRAMU
# ==============================================================================
def main():
    global is_wifi_connected, blink_state

    # Inicializace I2C0 (GP4 = SDA, GP5 = SCL) a UART0 (GP0 = TX, GP1 = RX)
    i2c = I2C(0, sda=Pin(I2C_SDA_PIN), scl=Pin(I2C_SCL_PIN), freq=100_000)
    oled = SH1106_I2C(i2c)
    gps_uart = UART(0, baudrate=9600, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))

    # Inicializace a kalibrace MPU6050
    imu = init_mpu6050(i2c)
    if imu is not None:
        oled.fill(0)
        oled.text("Kalibrace IMU...", 0, 28)
        oled.show()
        imu.calibrate(samples=50, delay_ms=10)

    # Úvodní vykreslení stavové lišty
    oled.fill(0)
    oled.hline(0, HEADER_LINE_Y, OLED_WIDTH, 1)
    draw_gps_icon(oled, False)
    draw_wifi_icon(oled, 4, visible=True)
    oled.show()

    # Časovač pro blikání ikony Wi-Fi při odpojení
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

    gps_data = create_gps_data()
    nmea_buffer = b""

    last_wifi_check = time.ticks_add(time.ticks_ms(), -WIFI_CHECK_MS)
    last_display_update = time.ticks_ms()
    last_imu_retry = time.ticks_ms()

    print("Spoustim system (Ctrl+C pro ukonceni)...")

    try:
        while True:
            now = time.ticks_ms()

            # 1. Průběžné čtení a parsování NMEA zpráv z GPS (UART0)
            if gps_uart.any():
                raw_bytes = gps_uart.read()
                if raw_bytes:
                    nmea_buffer += raw_bytes
                    while b"\n" in nmea_buffer:
                        line, nmea_buffer = nmea_buffer.split(b"\n", 1)
                        try:
                            sentence = line.decode("ascii").strip()
                            parse_nmea(sentence, gps_data)
                        except (UnicodeError, ValueError):
                            pass

            # 2. Pokus o znovupřipojení MPU6050, pokud nebyl nalezen při startu
            if imu is None and time.ticks_diff(now, last_imu_retry) >= 2000:
                last_imu_retry = now
                imu = init_mpu6050(i2c)
                if imu is not None:
                    imu.calibrate(samples=30, delay_ms=5)

            # 3. Kontrola Wi-Fi každých 5 sekund
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
                    rssi = wifi.status("rssi")
                    bars = rssi_to_bars(rssi)
                    draw_wifi_icon(oled, bars, visible=True)
                else:
                    is_wifi_connected = False

            # 4. Čtení z MPU6050 a aktualizace displeje každých 250 ms
            if time.ticks_diff(now, last_display_update) >= DISPLAY_UPDATE_MS:
                last_display_update = now

                gps_active = (
                    gps_data["last_update"] is not None
                    and time.ticks_diff(now, gps_data["last_update"]) < GPS_TIMEOUT_MS
                )
                draw_gps_icon(oled, gps_active)

                imu_data = None
                if imu is not None:
                    try:
                        imu_data = imu.read()
                    except Exception as e:
                        print("Chyba cteni MPU6050:", e)
                        imu = None  # Spustí automatické znovupřipojení

                draw_sensor_data(oled, gps_data, gps_active, imu_data)
                oled.show()

            time.sleep_ms(10)

    except KeyboardInterrupt:
        print("\nProgram ukoncen uzivatelem.")
    finally:
        blink_timer.deinit()
        wifi_utils.disconnect(wifi)
        oled.fill(0)
        oled.show()
        oled.poweroff()


if __name__ == "__main__":
    main()
