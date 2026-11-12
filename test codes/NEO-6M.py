from machine import UART
from time import sleep_ms

uart = UART(0, baudrate=9600, tx=0, rx=1)

buffer = b''

while True:
    if uart.any():
        data = uart.read()

        if data:
            buffer += data

            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)

                line = line.strip()

                if line.startswith(b'$'):
                    try:
                        print(line.decode('ascii'))
                    except UnicodeError:
                        print("Invalid characters received")

    sleep_ms(5)