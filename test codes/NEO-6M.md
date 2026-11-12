# NEO-6M – GPS Module

## 1. Component Description

The NEO-6M is a GPS (Global Positioning System) receiver module designed to determine geographical position, velocity and time using signals received from GPS satellites.

The module provides location and navigation information through NMEA (National Marine Electronics Association) sentences.

The GPS receiver provides the following information:

- Geographical latitude and longitude
- Altitude above sea level
- Current UTC time and date
- Number of satellites in view
- GPS fix status
- Speed and direction of movement

In this project, the NEO-6M GPS module is connected to a Raspberry Pi Pico W and programmed using MicroPython.

The module communicates with the microcontroller through a UART serial interface and transmits GPS data in the form of NMEA sentences.

## 2. Hardware Specifications

| Parameter | Value |
|-----------|-------|
| GPS Module | NEO-6M |
| Receiver | u-blox NEO-6M |
| Communication | UART |
| Default Baud Rate | 9600 baud |
| Data Format | NMEA 0183 |
| Supply Voltage | Depends on module version (typically 3.3–5 V) |
| Operating Frequency | 1575.42 MHz (GPS L1) |
| Position Accuracy | Approximately 2.5 m (under suitable conditions) |
| Microcontroller | Raspberry Pi Pico W |
| Programming Language | MicroPython |

## 3. Hardware Connections

| NEO-6M Pin | Raspberry Pi Pico W | Physical Pin |
|------------|---------------------|--------------|
| VCC | VBUS / 3V3 OUT (depending on module requirements) | 40 / 36 |
| GND | GND | 38 |
| TX | GP1 (UART0 RX) | 2 |
| RX | GP0 (UART0 TX) | 1 |

The GPS module communicates with the Raspberry Pi Pico W using the UART0 interface.

The TX pin of the GPS module is connected to the RX pin of the microcontroller, while the RX pin of the GPS module is connected to the TX pin.

Only the TX connection is required for receiving GPS data.

## 4. UART Communication Test

The UART interface was initialized using the following configuration:

- UART controller: UART0
- TX: GP0
- RX: GP1
- Baud rate: 9600
- Data format: NMEA 0183
- Communication: Serial UART

The Raspberry Pi Pico W continuously reads incoming serial data from the GPS module.

The received data is stored in a buffer and separated into individual lines using the newline character (`\n`).

Each complete line is checked to determine whether it starts with the `$` character, which indicates the beginning of an NMEA sentence.

Valid ASCII sentences are then decoded and displayed in the terminal.

## 5. GPS Module Testing

The NEO-6M was tested using the following MicroPython program.

### MicroPython Code

```python
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
```

The program performs the following operations:

1. Initializes UART0 communication at 9600 baud.
2. Configures GP0 as TX and GP1 as RX.
3. Continuously checks whether data is available from the GPS module.
4. Reads incoming serial data and stores it in a buffer.
5. Separates the received data into individual NMEA sentences.
6. Checks whether each sentence starts with `$`.
7. Decodes the received data using ASCII encoding.
8. Displays the NMEA sentences in the terminal.

### NMEA Sentence Types

The GPS module transmits several types of NMEA sentences.

| Sentence | Description |
|----------|-------------|
| GGA | GPS fix information, position and altitude |
| GSA | GPS fix mode and satellite information |
| GSV | Satellites in view |
| RMC | Recommended minimum navigation data |
| VTG | Course over ground and ground speed |
| GLL | Geographic position (latitude and longitude) |

These sentences contain the information required to determine the current GPS position and navigation status.

## 6. Experimental Results

The GPS module was tested indoors. The following NMEA sentences were successfully received and displayed in the terminal:

```text
$GPVTG,,,,,,,,,N*30
$GPGGA,,,,,,0,00,99.99,,,,,,*48
$GPGSA,A,1,,,,,,,,,,,,,99.99,99.99,99.99*30
$GPGSV,1,1,00*79
$GPGLL,,,,,,V,N*64
$GPRMC,,V,,,,,,,,,,N*53
```

The received sentences indicate that UART communication between the NEO-6M GPS module and the Raspberry Pi Pico W is working correctly.

However, the GPS receiver did not obtain a valid position fix during the indoor test.

### Interpretation of the Received Data

| NMEA Sentence | Observed Value | Meaning |
|---------------|----------------|---------|
| GGA | Fix quality: `0` | No GPS fix |
| GGA | Satellites: `00` | No satellites used for positioning |
| GSA | Fix mode: `1` | No fix |
| GSV | Satellites in view: `00` | No satellites detected |
| GLL | Status: `V` | Position data invalid |
| RMC | Status: `V` | Navigation data invalid |
| VTG | Mode: `N` | Data not valid |

The received sentences contain empty fields for latitude, longitude, altitude and other navigation parameters because the receiver has not established a valid GPS fix.

## 7. Results and Evaluation

### UART Communication

The NEO-6M successfully transmitted NMEA sentences to the Raspberry Pi Pico W.

The received data was correctly separated into individual sentences, decoded and displayed in the terminal.

This confirms that the UART interface is configured correctly and that serial communication between the two devices is functioning.

### GPS Reception

Although communication was successful, the GPS module did not obtain a valid position fix during testing.

The GGA sentence reported a fix quality of `0`, while the GSA sentence indicated fix mode `1`. Additionally, the GSV sentence reported zero satellites in view.

The RMC and GLL sentences both contained the status indicator `V`, which means that the navigation data is invalid.

This result is expected under indoor testing conditions because GPS signals are relatively weak and can be significantly attenuated by roofs, walls and other building structures.

### Conclusion

The initial test successfully verified the hardware connection and UART communication between the NEO-6M GPS module and the Raspberry Pi Pico W.

However, the GPS receiver was unable to determine its geographical position indoors due to insufficient satellite reception.

Further testing will be performed outdoors, where the GPS antenna has a clearer view of the sky. Under suitable reception conditions, the module should be able to acquire satellite signals and provide valid position, altitude, speed and time information.

A subsequent step will be to parse the received NMEA sentences to extract latitude, longitude and other GPS parameters for use in the project.