# NEO-6M – GPS Module

## 1. Component Description

The NEO-6M is a GPS (Global Positioning System) receiver module designed to determine geographical position, velocity and time using signals received from GPS satellites.

The GPS receiver provides the following information:

- Geographical latitude and longitude
- Altitude above sea level
- Current UTC time and date
- Number of satellites in view
- GPS fix status
- Speed and direction of movement

The module communicates with the microcontroller through a UART serial interface.

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

## 3. Hardware Connections

| NEO-6M Pin | Raspberry Pi Pico W | Physical Pin |
|------------|---------------------|--------------|
| VCC | 3V3 | 36 |
| GND | GND | 38 |
| TX | GP1 (UART0 RX) | 2 |
| RX | GP0 (UART0 TX) | 1 |

The GPS module communicates with the Raspberry Pi Pico W using the UART0 interface.

The TX pin of the GPS module is connected to the RX pin of the microcontroller, while the RX pin of the GPS module is connected to the TX pin.

## 4. GPS Module Testing

The NEO-6M was tested using the following MicroPython program.

### MicroPython Code

The [file](NEO-6M.py).

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

## 5. Experimental Results

The GPS module was tested indoors. The following NMEA sentences were successfully received and displayed in the terminal:

```
$GPVTG,,,,,,,,,N*30
$GPGGA,,,,,,0,00,99.99,,,,,,*48
$GPGSA,A,1,,,,,,,,,,,,,99.99,99.99,99.99*30
$GPGSV,1,1,00*79
$GPGLL,,,,,,V,N*64
$GPRMC,,V,,,,,,,,,,N*53
```

The received sentences indicate that UART communication between the NEO-6M GPS module and the Raspberry Pi Pico W is working correctly.

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

## 6. Results and Evaluation

### UART Communication

The NEO-6M successfully transmitted NMEA sentences to the Raspberry Pi Pico W.

The received data was correctly separated into individual sentences, decoded and displayed in the terminal.

This confirms that the UART interface is configured correctly and that serial communication between the two devices is functioning.

### GPS Reception

Although communication was successful, the GPS module did not obtain a valid position fix during testing.

The GGA sentence reported a fix quality of `0`, while the GSA sentence indicated fix mode `1`. Additionally, the GSV sentence reported zero satellites in view.

The RMC and GLL sentences both contained the status indicator `V`, which means that the navigation data is invalid.

This result is expected under indoor testing conditions because GPS signals are relatively weak and can be attenuated by roofs and walls.

### Conclusion

The initial test successfully verified the hardware connection and UART communication between the NEO-6M GPS module and the Raspberry Pi Pico W.

NMEA sentences will need to be parsed to obtain useful data, but the module works and we have a way to interface with it.
