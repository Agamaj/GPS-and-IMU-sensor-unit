from machine import Pin, I2C
import time
import struct

i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100000)
MPU_ADDR = 0x68

#Wake up MPU-6050
i2c.writeto_mem(MPU_ADDR, 0x6B, b'\x00')
time.sleep_ms(100)

def read_sensor():
    data = i2c.readfrom_mem(MPU_ADDR, 0x3B, 14)
    ax, ay, az, temp, gx, gy, gz = struct.unpack(">hhhhhhh", data)
    ax = ax / 16384 * 9.80665
    ay = ay / 16384 * 9.80665
    az = az / 16384 * 9.80665
    
    gx = gx / 131.0
    gy = gy / 131.0
    gz = gz / 131.0

    return ax, ay, az, gx, gy, gz
#yroscope calibration
print("Keep the sensor still...")
samples = 200
offset_x = 0
offset_y = 0
offset_z = 0

for i in range(samples):
    ax, ay, az, gx, gy, gz = read_sensor()
    offset_x += gx
    offset_y += gy
    offset_z += gz
    
    time.sleep_ms(10)

offset_x /= samples
offset_y /= samples
offset_z /= samples

print("Calibration completed!")
print("Offsets:", offset_x, offset_y, offset_z)

while True:
    ax, ay, az, gx, gy, gz = read_sensor()
    gx -= offset_x
    gy -= offset_y
    gz -= offset_z
    print("Acceleration [m/s^2]:")
    print("X: {:.2f} Y: {:.2f} Z: {:.2f}".format(ax, ay, az))
    print("Gyroscope [deg/s]:")
    print("X: {:.2f} Y: {:.2f} Z: {:.2f}".format(gx, gy, gz))
    print("--------------------")
    time.sleep(1)
