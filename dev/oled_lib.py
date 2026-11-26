from sh1106 import SH1106_I2C
import math
import time

OLED_WIDTH = 128
OLED_HEIGHT = 64

ICON_X = OLED_WIDTH - 14  # x = 114
ICON_Y = 0                # y = 0
GPS_X = ICON_X - 27       # x = 87
GPS_Y = 2                 # y = 2
HEADER_LINE_Y = 13

# Minimální posun v metrech pro aktualizaci směru chůze (filtruje drift GPS v klidu)
MIN_MOVE_METERS = 2.5


class OledDisplay:
    def __init__(self, i2c):
        self.oled = SH1106_I2C(i2c)

        # Stavové proměnné pro výpočet směru pohybu a nadmořské výšky z GPS
        self.ref_lat = None
        self.ref_lon = None
        self.bearing = None
        self.is_moving = False
        self.last_move_ms = 0
        self.total_distance = 0.0

        self.filtered_alt = None
        self.base_alt = None

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

    @staticmethod
    def _bearing_to_cardinal(deg):
        dirs = ("S ", "SV", "V ", "JV", "J ", "JZ", "Z ", "SZ")
        idx = int((deg + 22.5) // 45) % 8
        return dirs[idx]

    def reset_navigation(self):
        """Vynuluje výchozí bod pro měření směru a převýšení."""
        self.ref_lat = None
        self.ref_lon = None
        self.bearing = None
        self.is_moving = False
        self.total_distance = 0.0
        self.base_alt = self.filtered_alt

    def update_navigation(self, gps_data, has_fix):
        """
        Průběžně počítá směr chůze (azimut) ze změny GPS souřadnic
        a vyhlazenou nadmořskou výšku + převýšení.
        """
        if not has_fix:
            self.is_moving = False
            return

        # 1. Výpočet vyhlazené nadmořské výšky a relativního převýšení
        raw_alt = gps_data.get("altitude")
        if raw_alt is not None:
            if self.filtered_alt is None:
                self.filtered_alt = raw_alt
            else:
                self.filtered_alt = 0.8 * self.filtered_alt + 0.2 * raw_alt

            if self.base_alt is None:
                self.base_alt = self.filtered_alt

        # 2. Výpočet směru pohybu ze změny zeměpisné šířky a délky
        lat = gps_data.get("latitude")
        lon = gps_data.get("longitude")
        if lat is None or lon is None:
            return

        if self.ref_lat is None or self.ref_lon is None:
            self.ref_lat = lat
            self.ref_lon = lon
            return

        # Přepočet rozdílu souřadnic na metry (dx = východ, dy = sever)
        mean_lat_rad = math.radians((self.ref_lat + lat) * 0.5)
        dy = math.radians(lat - self.ref_lat) * 6371000.0
        dx = math.radians(lon - self.ref_lon) * 6371000.0 * math.cos(mean_lat_rad)
        dist = math.sqrt(dx * dx + dy * dy)

        now = time.ticks_ms()
        if dist >= MIN_MOVE_METERS:
            self.bearing = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
            self.total_distance += dist
            self.ref_lat = lat
            self.ref_lon = lon
            self.is_moving = True
            self.last_move_ms = now
        elif time.ticks_diff(now, self.last_move_ms) > 6000:
            self.is_moving = False

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
        """REŽIM 0: Textová data z GPS a MPU6050."""
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
            ax = imu_data["linear_accel"]["x"]
            ay = imu_data["linear_accel"]["y"]
            az = imu_data["linear_accel"]["z"]
            gx = imu_data["gyro"]["x"]
            gy = imu_data["gyro"]["y"]
            gz = imu_data["gyro"]["z"]

            ax = 0.0 if abs(ax) < 0.05 else ax
            ay = 0.0 if abs(ay) < 0.05 else ay
            az = 0.0 if abs(az) < 0.05 else az
            gx = 0.0 if abs(gx) < 0.5 else gx
            gy = 0.0 if abs(gy) < 0.5 else gy
            gz = 0.0 if abs(gz) < 0.5 else gz

            self.oled.text(f"A:{ax:4.1f} {ay:4.1f} {az:4.1f}", 0, 41)
            self.oled.text(f"G:{gx:4.0f} {gy:4.0f} {gz:4.0f}", 0, 52)
        else:
            self.oled.text("IMU: Odpojeno", 0, 41)
            self.oled.text("Hledam I2C...", 0, 52)

    def _draw_compass_circle(self, cx, cy, r):
        """Vykreslí obrys kompasu a značky světových stran."""
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            x = int(round(cx + math.sin(rad) * r))
            y = int(round(cy - math.cos(rad) * r))
            self.oled.pixel(x, y, 1)

        # Výraznější značky pro V, J, Z (sever má nahoře písmeno N)
        self.oled.hline(cx + r - 2, cy, 3, 1)
        self.oled.vline(cx, cy + r - 2, 3, 1)
        self.oled.hline(cx - r, cy, 3, 1)

    def draw_motion_arrow_screen(self, gps_data, has_fix=True, imu_data=None):
        """
        REŽIM 1: Vykreslí šipku směru chůze ze změny GPS souřadnic,
        rychlost a vypočítanou nadmořskou výšku + převýšení.
        """
        self.clear_body()

        # Levý sloupec textových údajů (max 8 znaků = 64 px -> nezasahuje do kompasu)
        spd = gps_data.get("speed_kmh")
        if spd is None and gps_data.get("speed_knots") is not None:
            spd = gps_data["speed_knots"] * 1.852
        spd = spd or 0.0

        # 1. Směr a azimut
        if self.bearing is not None:
            card = self._bearing_to_cardinal(self.bearing)
            self.oled.text(f"{card}{int(round(self.bearing)):03d}st", 0, 17)
        elif not has_fix:
            self.oled.text("GPS Fix?", 0, 17)
        else:
            self.oled.text("Jdi >3m", 0, 17)

        # 2. Rychlost chůze
        self.oled.text(f"{spd:4.1f}km/h", 0, 29)

        # 3. Vypočítaná nadmořská výška
        if self.filtered_alt is not None:
            self.oled.text(f"Alt:{int(round(self.filtered_alt))}m", 0, 42)
        else:
            self.oled.text("Alt:---m", 0, 42)

        # 4. Vypočítaná změna výšky oproti startu (převýšení)
        if self.filtered_alt is not None and self.base_alt is not None:
            delta_alt = self.filtered_alt - self.base_alt
            self.oled.text(f"dH:{delta_alt:+4.1f}m", 0, 54)
        else:
            self.oled.text("dH: ---", 0, 54)

        # Pravá strana: kruhový kompas se šipkou směru chůze
        cx = 100
        cy = 40
        r = 16

        self.oled.text("N", cx - 3, 15)
        self._draw_compass_circle(cx, cy, r)

        if self.bearing is None:
            # Dokud se zařízení nepohne o 2,5 m, svítí jen středový bod
            self.oled.fill_rect(cx - 1, cy - 1, 3, 3, 1)
            return

        # Směrový vektor šipky (0° = nahoru k N, 90° = doprava)
        rad = math.radians(self.bearing)
        ux = math.sin(rad)
        uy = -math.cos(rad)

        arrow_len = r - 3
        ex = int(round(cx + ux * arrow_len))
        ey = int(round(cy + uy * arrow_len))
        sx = int(round(cx - ux * (arrow_len // 2)))
        sy = int(round(cy - uy * (arrow_len // 2)))

        # Tělo šipky
        px = int(round(-uy))
        py = int(round(ux))
        self.oled.line(sx, sy, ex, ey, 1)
        self.oled.line(sx + px, sy + py, ex + px, ey + py, 1)

        # Špička šipky
        head_len = 5
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
