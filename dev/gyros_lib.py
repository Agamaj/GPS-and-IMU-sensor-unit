from machine import I2C
import math
import struct
import time


class MPU6050:
    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address
        self.gyro_offset = [0.0, 0.0, 0.0]
        self.gravity = [0.0, 0.0, 9.80665]
        self.linear_accel = [0.0, 0.0, 0.0]
        self.last_update_ms = time.ticks_ms()

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

    def calibrate(self, samples=60, delay_ms=10):
        """Změří klidový offset gyroskopu a počáteční směr gravitace."""
        g_offsets = [0.0, 0.0, 0.0]
        grav_acc = [0.0, 0.0, 0.0]

        for _ in range(samples):
            ax, ay, az, _, gx, gy, gz = self.read_raw()
            grav_acc[0] += (ax / 16384.0) * 9.80665
            grav_acc[1] += (ay / 16384.0) * 9.80665
            grav_acc[2] += (az / 16384.0) * 9.80665

            g_offsets[0] += gx / 131.0
            g_offsets[1] += gy / 131.0
            g_offsets[2] += gz / 131.0
            time.sleep_ms(delay_ms)

        self.gravity = [val / samples for val in grav_acc]
        self.gyro_offset = [val / samples for val in g_offsets]
        self.linear_accel = [0.0, 0.0, 0.0]
        self.last_update_ms = time.ticks_ms()
        return self.gyro_offset

    def read(self):
        """
        Přečte senzor, aktualizuje odhad gravitace pomocí komplementárního filtru
        a vrátí surové zrychlení, čisté lineární zrychlení (bez gravitace) a gyroskop.
        """
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self.last_update_ms) / 1000.0
        self.last_update_ms = now
        if dt <= 0.0 or dt > 0.25:
            dt = 0.02

        ax, ay, az, _, gx, gy, gz = self.read_raw()

        # Surové zrychlení [m/s^2]
        raw_ax = (ax / 16384.0) * 9.80665
        raw_ay = (ay / 16384.0) * 9.80665
        raw_az = (az / 16384.0) * 9.80665

        # Úhlová rychlost [deg/s]
        gyro_x = (gx / 131.0) - self.gyro_offset[0]
        gyro_y = (gy / 131.0) - self.gyro_offset[1]
        gyro_z = (gz / 131.0) - self.gyro_offset[2]

        # Rotace vektoru gravitace podle gyroskopu (rad/s)
        wx = math.radians(gyro_x)
        wy = math.radians(gyro_y)
        wz = math.radians(gyro_z)

        gx_est, gy_est, gz_est = self.gravity
        g_gyro_x = gx_est - (wy * gz_est - wz * gy_est) * dt
        g_gyro_y = gy_est - (wz * gx_est - wx * gz_est) * dt
        g_gyro_z = gz_est - (wx * gy_est - wy * gx_est) * dt

        # Komplementární filtr (odfiltruje vliv náklonu i dlouhodobý drift)
        alpha = 0.94
        gx_est = alpha * g_gyro_x + (1.0 - alpha) * raw_ax
        gy_est = alpha * g_gyro_y + (1.0 - alpha) * raw_ay
        gz_est = alpha * g_gyro_z + (1.0 - alpha) * raw_az
        self.gravity = [gx_est, gy_est, gz_est]

        # Čisté lineární zrychlení pohybu po odečtení gravitace
        lin_x = raw_ax - gx_est
        lin_y = raw_ay - gy_est
        lin_z = raw_az - gz_est

        # Jemné vyhlazení proti vibracím
        smooth = 0.65
        self.linear_accel[0] = (1.0 - smooth) * self.linear_accel[0] + smooth * lin_x
        self.linear_accel[1] = (1.0 - smooth) * self.linear_accel[1] + smooth * lin_y
        self.linear_accel[2] = (1.0 - smooth) * self.linear_accel[2] + smooth * lin_z

        return {
            "accel": {
                "x": raw_ax,
                "y": raw_ay,
                "z": raw_az
            },
            "linear_accel": {
                "x": self.linear_accel[0],
                "y": self.linear_accel[1],
                "z": self.linear_accel[2]
            },
            "gyro": {
                "x": gyro_x,
                "y": gyro_y,
                "z": gyro_z
            }
        }


def init_mpu6050(i2c):
    """Vyhledá MPU6050 na sběrnici I2C (adresa 0x68 nebo 0x69) a inicializuje ho."""
    devices = i2c.scan()
    for addr in (0x68, 0x69):
        if addr in devices:
            try:
                return MPU6050(i2c, address=addr)
            except Exception as e:
                print(f"Chyba inicializace MPU6050 na {hex(addr)}:", e)
    return None
