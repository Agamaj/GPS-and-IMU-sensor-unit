from sh1106 import SH1106_I2C
import math

OLED_WIDTH = 128
OLED_HEIGHT = 64
HEADER_LINE_Y = 13
ICON_X = OLED_WIDTH - 14
GPS_X = ICON_X - 27
MIN_MOVE_M = 2.5
DIRS = ("S ", "SV", "V ", "JV", "J ", "JZ", "Z ", "SZ")


class OledDisplay:
    def __init__(self, i2c):
        self.oled = SH1106_I2C(i2c)
        self.ref_lat = None
        self.ref_lon = None
        self.bearing = None
        self.filtered_alt = None
        self.base_alt = None

    @staticmethod
    def rssi_to_bars(rssi):
        if rssi is None:
            return 0
        rssi = round(rssi)
        if rssi >= -55:
            return 4
        if rssi >= -67:
            return 3
        if rssi >= -78:
            return 2
        return 1

    def update_navigation(self, gps_data, has_fix):
        if not has_fix:
            return

        raw_alt = gps_data.get("altitude")
        if raw_alt is not None:
            self.filtered_alt = raw_alt if self.filtered_alt is None else 0.8 * self.filtered_alt + 0.2 * raw_alt
            if self.base_alt is None:
                self.base_alt = self.filtered_alt

        lat = gps_data.get("latitude")
        lon = gps_data.get("longitude")
        if lat is None or lon is None:
            return

        if self.ref_lat is None or self.ref_lon is None:
            self.ref_lat, self.ref_lon = lat, lon
            return

        mean_lat = math.radians((self.ref_lat + lat) * 0.5)
        dy = math.radians(lat - self.ref_lat) * 6371000.0
        dx = math.radians(lon - self.ref_lon) * 6371000.0 * math.cos(mean_lat)
        if math.sqrt(dx * dx + dy * dy) >= MIN_MOVE_M:
            self.bearing = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
            self.ref_lat, self.ref_lon = lat, lon

    def clear_all(self):
        self.oled.fill(0)

    def clear_body(self):
        self.oled.fill_rect(0, HEADER_LINE_Y + 2, OLED_WIDTH, OLED_HEIGHT - (HEADER_LINE_Y + 2), 0)

    def draw_header_line(self):
        self.oled.hline(0, HEADER_LINE_Y, OLED_WIDTH, 1)

    def draw_message(self, text, x=0, y=28):
        self.clear_all()
        self.oled.text(text, x, y)
        self.oled.show()

    def draw_time(self, gps_data, gps_active):
        self.oled.fill_rect(0, 0, 70, 12, 0)
        t = gps_data.get("time") if gps_active else None
        if t and len(t) >= 6:
            self.oled.text(f"{t[0:2]}:{t[2:4]}:{t[4:6]}", 0, 2)

    def draw_wifi_icon(self, bars, visible=True):
        self.oled.fill_rect(ICON_X - 1, 0, 16, 12, 0)
        if not visible or bars <= 0:
            return
        cx = ICON_X + 6
        if bars >= 1:
            self.oled.fill_rect(cx, 9, 2, 2, 1)
        if bars >= 2:
            self.oled.hline(cx - 1, 6, 4, 1)
            self.oled.pixel(cx - 2, 7, 1)
            self.oled.pixel(cx + 3, 7, 1)
        if bars >= 3:
            self.oled.hline(cx - 2, 3, 6, 1)
            self.oled.pixel(cx - 3, 4, 1)
            self.oled.pixel(cx + 4, 4, 1)
            self.oled.pixel(cx - 4, 5, 1)
            self.oled.pixel(cx + 5, 5, 1)
        if bars >= 4:
            self.oled.hline(cx - 2, 0, 6, 1)
            self.oled.hline(cx - 4, 1, 2, 1)
            self.oled.hline(cx + 4, 1, 2, 1)
            self.oled.pixel(cx - 5, 2, 1)
            self.oled.pixel(cx + 6, 2, 1)
            self.oled.pixel(cx - 6, 3, 1)
            self.oled.pixel(cx + 7, 3, 1)

    def draw_gps_icon(self, connected):
        self.oled.fill_rect(GPS_X - 3, 0, 28, 12, 0)
        if connected:
            self.oled.text("GPS", GPS_X, 2, 1)

    def draw_sensor_data(self, gps_data, gps_active, has_fix, imu_data):
        self.clear_body()
        lat, lon = gps_data.get("latitude"), gps_data.get("longitude")
        sats = gps_data.get("satellites") or 0
        sats_v = gps_data.get("satellites_in_view") or 0
        spd = gps_data.get("speed_kmh")
        if spd is None and gps_data.get("speed_knots") is not None:
            spd = gps_data["speed_knots"] * 1.852
        spd = spd or 0.0

        if not gps_active:
            self.oled.text("GPS: Odpojeno", 0, 16)
            self.oled.text("Cekam na UART...", 0, 26)
        elif has_fix and lat is not None and lon is not None:
            self.oled.text(f"La:{lat:7.4f} S:{sats:02d}", 0, 16)
            self.oled.text(f"Lo:{lon:7.4f} {spd:3.0f}km", 0, 26)
        else:
            msg = gps_data.get("last_sentence") or ""
            self.oled.text(f"GPS: NoFix {msg}", 0, 16)
            self.oled.text(f"Sat:{sats}/{sats_v:02d}", 0, 26)

        self.oled.hline(0, 37, OLED_WIDTH, 1)

        if imu_data is not None:
            la, g = imu_data["linear_accel"], imu_data["gyro"]
            ax = 0.0 if abs(la["x"]) < 0.05 else la["x"]
            ay = 0.0 if abs(la["y"]) < 0.05 else la["y"]
            az = 0.0 if abs(la["z"]) < 0.05 else la["z"]
            gx = 0.0 if abs(g["x"]) < 0.5 else g["x"]
            gy = 0.0 if abs(g["y"]) < 0.5 else g["y"]
            gz = 0.0 if abs(g["z"]) < 0.5 else g["z"]
            self.oled.text(f"A:{ax:4.1f} {ay:4.1f} {az:4.1f}", 0, 41)
            self.oled.text(f"G:{gx:4.0f} {gy:4.0f} {gz:4.0f}", 0, 52)
        else:
            self.oled.text("IMU: Odpojeno", 0, 41)
            self.oled.text("Hledam I2C...", 0, 52)

    def draw_gps_arrow_screen(self, gps_data, has_fix=True):
        self.clear_body()
        spd = gps_data.get("speed_kmh")
        if spd is None and gps_data.get("speed_knots") is not None:
            spd = gps_data["speed_knots"] * 1.852
        spd = spd or 0.0

        if self.bearing is not None:
            card = DIRS[int((self.bearing + 22.5) // 45) % 8]
            self.oled.text(f"{card}{int(round(self.bearing)):03d}st", 0, 17)
        else:
            self.oled.text("GPS Fix?" if not has_fix else "Jdi >3m", 0, 17)

        self.oled.text(f"{spd:4.1f}km/h", 0, 29)
        self.oled.text(f"Alt:{int(round(self.filtered_alt))}m" if self.filtered_alt is not None else "Alt:---m", 0, 42)
        if self.filtered_alt is not None and self.base_alt is not None:
            self.oled.text(f"dH:{self.filtered_alt - self.base_alt:+4.1f}m", 0, 54)
        else:
            self.oled.text("dH: ---", 0, 54)

        cx, cy, r = 100, 40, 16
        self.oled.text("N", cx - 3, 15)
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            self.oled.pixel(int(round(cx + math.sin(rad) * r)), int(round(cy - math.cos(rad) * r)), 1)
        self.oled.hline(cx + r - 2, cy, 3, 1)
        self.oled.vline(cx, cy + r - 2, 3, 1)
        self.oled.hline(cx - r, cy, 3, 1)

        if self.bearing is None:
            self.oled.fill_rect(cx - 1, cy - 1, 3, 3, 1)
            return

        rad = math.radians(self.bearing)
        ux, uy = math.sin(rad), -math.cos(rad)
        ex, ey = int(round(cx + ux * (r - 3))), int(round(cy + uy * (r - 3)))
        sx, sy = int(round(cx - ux * 6)), int(round(cy - uy * 6))
        px, py = int(round(-uy)), int(round(ux))
        self.oled.line(sx, sy, ex, ey, 1)
        self.oled.line(sx + px, sy + py, ex + px, ey + py, 1)

        ang = math.atan2(uy, ux)
        lx, ly = int(round(ex + math.cos(ang + 2.6) * 5)), int(round(ey + math.sin(ang + 2.6) * 5))
        rx, ry = int(round(ex + math.cos(ang - 2.6) * 5)), int(round(ey + math.sin(ang - 2.6) * 5))
        self.oled.line(ex, ey, lx, ly, 1)
        self.oled.line(ex, ey, rx, ry, 1)
        self.oled.line(lx, ly, rx, ry, 1)

    def show(self):
        self.oled.show()

    def poweroff(self):
        self.oled.fill(0)
        self.oled.show()
        self.oled.poweroff()
