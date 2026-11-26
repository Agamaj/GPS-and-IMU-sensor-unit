from sh1106 import SH1106_I2C
import math

OLED_WIDTH = 128
OLED_HEIGHT = 64

ICON_X = OLED_WIDTH - 14  # x = 114
ICON_Y = 0                # y = 0
GPS_X = ICON_X - 27       # x = 87
GPS_Y = 2                 # y = 2
HEADER_LINE_Y = 13


class OledDisplay:
    def __init__(self, i2c):
        self.oled = SH1106_I2C(i2c)

    @staticmethod
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

    @staticmethod
    def _format_time(raw_time):
        if not raw_time or len(raw_time) < 6:
            return "--:--:--"
        return f"{raw_time[0:2]}:{raw_time[2:4]}:{raw_time[4:6]}"

    def clear_all(self):
        self.oled.fill(0)

    def clear_body(self):
        """Vymaže pouze datovou oblast pod horní stavovou lištou (ikony zůstanou)."""
        self.oled.fill_rect(
            0, HEADER_LINE_Y + 2, OLED_WIDTH, OLED_HEIGHT - (HEADER_LINE_Y + 2), 0
        )

    def draw_header_line(self):
        self.oled.hline(0, HEADER_LINE_Y, OLED_WIDTH, 1)

    def draw_message(self, text, x=0, y=28):
        self.clear_all()
        self.oled.text(text, x, y)
        self.oled.show()

    def draw_wifi_icon(self, bars, visible=True):
        self.oled.fill_rect(ICON_X - 1, ICON_Y, 16, 12, 0)
        if not visible or bars <= 0:
            return

        cx = ICON_X + 6
        y = ICON_Y

        if bars >= 1:
            self.oled.fill_rect(cx, y + 9, 2, 2, 1)
        if bars >= 2:
            self.oled.hline(cx - 1, y + 6, 4, 1)
            self.oled.pixel(cx - 2, y + 7, 1)
            self.oled.pixel(cx + 3, y + 7, 1)
        if bars >= 3:
            self.oled.hline(cx - 2, y + 3, 6, 1)
            self.oled.pixel(cx - 3, y + 4, 1)
            self.oled.pixel(cx + 4, y + 4, 1)
            self.oled.pixel(cx - 4, y + 5, 1)
            self.oled.pixel(cx + 5, y + 5, 1)
        if bars >= 4:
            self.oled.hline(cx - 2, y, 6, 1)
            self.oled.hline(cx - 4, y + 1, 2, 1)
            self.oled.hline(cx + 4, y + 1, 2, 1)
            self.oled.pixel(cx - 5, y + 2, 1)
            self.oled.pixel(cx + 6, y + 2, 1)
            self.oled.pixel(cx - 6, y + 3, 1)
            self.oled.pixel(cx + 7, y + 3, 1)

    def draw_gps_icon(self, connected):
        self.oled.fill_rect(GPS_X - 3, 0, 28, 12, 0)
        if connected:
            self.oled.text("GPS", GPS_X, GPS_Y, 1)

    def draw_sensor_data(self, gps_data, gps_active, has_fix, imu_data):
        """REŽIM 0: Textová data z vašeho gps_lib.py a MPU6050."""
        self.clear_body()

        lat = gps_data.get("latitude")
        lon = gps_data.get("longitude")
        sats_used = gps_data.get("satellites") or 0
        sats_view = gps_data.get("satellites_in_view") or 0
        utc_str = self._format_time(gps_data.get("time"))

        spd = gps_data.get("speed_kmh")
        if spd is None and gps_data.get("speed_knots") is not None:
            spd = gps_data["speed_knots"] * 1.852
        spd = spd or 0.0

        if not gps_active:
            self.oled.text("GPS: Odpojeno", 0, 16)
            self.oled.text("Cekam na UART...", 0, 26)
        elif has_fix and lat is not None and lon is not None:
            self.oled.text(f"La:{lat:7.4f} S:{sats_used:02d}", 0, 16)
            self.oled.text(f"Lo:{lon:7.4f} {spd:3.0f}km", 0, 26)
        else:
            msg = gps_data.get("last_sentence") or "---"
            self.oled.text(f"UTC {utc_str} {msg}", 0, 16)
            self.oled.text(f"Sat:{sats_used}/{sats_view:02d} NoFix", 0, 26)

        self.oled.hline(0, 37, OLED_WIDTH, 1)

        if imu_data is not None:
            ax = imu_data["accel"]["x"]
            ay = imu_data["accel"]["y"]
            az = imu_data["accel"]["z"]
            gx = imu_data["gyro"]["x"]
            gy = imu_data["gyro"]["y"]
            gz = imu_data["gyro"]["z"]

            self.oled.text(f"A:{ax:4.1f} {ay:4.1f} {az:4.1f}", 0, 41)
            self.oled.text(f"G:{gx:4.0f} {gy:4.0f} {gz:4.0f}", 0, 52)
        else:
            self.oled.text("IMU: Odpojeno", 0, 41)
            self.oled.text("Hledam I2C...", 0, 52)

    def draw_motion_arrow_screen(self, gps_data, imu_data):
        """
        REŽIM 1: Vykreslí šipku směru a velikosti lineárního zrychlení v osách X, Y
        uprostřed displeje a nadmořskou výšku (osa Z) z GPS v levém dolním rohu.
        """
        self.clear_body()

        cx = OLED_WIDTH // 2  # x = 64
        cy = 38               # Střed plochy pod lištou

        alt = gps_data.get("altitude")
        if alt is not None:
            self.oled.text(f"Alt:{alt:.1f}m", 0, 55)
        else:
            self.oled.text("Alt: --- m", 0, 55)

        if imu_data is None:
            self.oled.text("IMU Chyba", 30, 35)
            return

        ax = imu_data["linear_accel"]["x"]
        ay = imu_data["linear_accel"]["y"]
        magnitude = math.sqrt(ax * ax + ay * ay)

        self.oled.text(f"a:{magnitude:3.1f}", 0, 16)

        max_len = 21
        self.oled.pixel(cx - max_len, cy, 1)
        self.oled.pixel(cx + max_len, cy, 1)
        self.oled.pixel(cx, cy - max_len, 1)
        self.oled.pixel(cx, cy + max_len, 1)

        if magnitude < 0.25:
            self.oled.fill_rect(cx - 1, cy - 1, 3, 3, 1)
            return

        min_len = 5
        length = min(max_len, max(min_len, int(round(magnitude * 4.5))))

        ux = ax / magnitude
        uy = -ay / magnitude

        ex = int(round(cx + ux * length))
        ey = int(round(cy + uy * length))

        px = int(round(-uy))
        py = int(round(ux))
        self.oled.line(cx, cy, ex, ey, 1)
        self.oled.line(cx + px, cy + py, ex + px, ey + py, 1)

        head_len = min(7, max(4, length // 3))
        angle = math.atan2(uy, ux)
        lx = int(round(ex + math.cos(angle + 2.6) * head_len))
        ly = int(round(ey + math.sin(angle + 2.6) * head_len))
        rx = int(round(ex + math.cos(angle - 2.6) * head_len))
        ry = int(round(ey + math.sin(angle - 2.6) * head_len))

        self.oled.line(ex, ey, lx, ly, 1)
        self.oled.line(ex, ey, rx, ry, 1)
        self.oled.line(lx, ly, rx, ry, 1)

    def show(self):
        self.oled.show()

    def poweroff(self):
        self.oled.fill(0)
        self.oled.show()
        self.oled.poweroff()
