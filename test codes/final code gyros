from machine import I2C
import time
import struct


class MPU6050:
    ADDRESS = 0x68

    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address

        self.gyro_offset = [0.0, 0.0, 0.0]

        # Wake up sensor
        self.i2c.writeto_mem(
            self.address, 0x6B, b'\x00'
        )

        # Accelerometer range: +/- 2g
        self.i2c.writeto_mem(
            self.address, 0x1C, b'\x00'
        )

        # Gyroscope range: +/- 250 deg/s
        self.i2c.writeto_mem(
            self.address, 0x1B, b'\x00'
        )

        time.sleep_ms(100)

    def read_raw(self):
        data = self.i2c.readfrom_mem(
            self.address, 0x3B, 14
        )

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

    def calibrate(self, samples=200, delay_ms=10):
        offsets = [0.0, 0.0, 0.0]

        for _ in range(samples):
            raw = self.read_raw()

            offsets[0] += raw[4] / 131.0
            offsets[1] += raw[5] / 131.0
            offsets[2] += raw[6] / 131.0

            time.sleep_ms(delay_ms)

        self.gyro_offset = [
            value / samples for value in offsets
        ]

        return self.gyro_offset
