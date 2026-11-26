# GPS and IMU Sensor Unit

### Device funcionality

Every second, MCU reads sensor raw data and computes exact location, acceleration/speed, direction of the movement. Results will be shown on the OLED display clearly. We also may add a small arrow showing a direction of the movement or a GPS and WiFi sign for indicating network stability - all of this is optional and doesn't need to be included in the code.

###  Program Functionality and Timing

The main application integrates the GPS NEO-6M,
MPU-6050 and SSD1306 OLED display using MicroPython
on the Raspberry Pi Pico W.

The program uses a non-blocking main loop with
periodically scheduled operations based on
  `time.ticks_ms()`.

###  Task Scheduling

| Task | Interval | Description |
|------|----------|-------------|
| GPS data processing | Every main loop iteration | Processes incoming NMEA data. |
| IMU measurement | 20 ms (50 Hz) | Reads acceleration and angular velocity from MPU-6050. |
| OLED update | 150 ms (~6.67 Hz) | Updates sensor data, navigation and status icons. |
| Wi-Fi connection check | 5000 ms (5 s) | Checks connection status and attempts reconnection if necessary. |
| Wi-Fi icon blinking | 750 ms | Indicates disconnected Wi-Fi using a periodic timer. |
| GPS data timeout | 3000 ms (3 s) | Determines whether received GPS data is recent. |
| Button debounce | 250 ms | Prevents unintended multiple screen switches. |
| IMU reconnection attempt | 2000 ms (2 s) | Attempts to restore communication with MPU-6050. |
| Initial IMU calibration | Once at startup (~600 ms) | Calculates offsets using 60 samples with a 10 ms delay. |
| IMU recalibration | After reconnection (~200 ms) | Uses 40 samples with a 5 ms delay. |
| Main loop delay | 5 ms | Reduces unnecessary CPU usage. |


### Member roles

- Tadeas Klimt -  oled_lib.py -> Graphical user interface + main.py responsibility, overall repository. 
- Josef Cvejn  -  gyros_lib.py -> Gyroscope calibration & library + repository (components and links).
- Pavel Curda  -  gps_lib.py -> GPS module initialization and parsing library, main device schematic.

###  Timing and Concurrency

The application uses cooperative task scheduling based on
`time.ticks_ms()` and `time.ticks_diff()`.

Individual operations are executed at predefined intervals
within the main loop. A separate periodic hardware timer
controls the blinking Wi-Fi status icon.

The display mode is controlled manually using a push button
connected to GPIO17.

The specified intervals represent nominal software timing.
Actual execution times may vary depending on communication,
sensor calibration and Wi-Fi reconnection.


###  Error Handling

The program includes basic error handling:

-	Invalid GPS fixes are clearly indicated.
-	Outdated GPS coordinates are rejected.
-	I2C devices are checked during initialization.
-	Sensor communication errors are reported.
-	Unavailable IMU data is not displayed as a valid measurement.

**Note:** The listed intervals are software scheduling
targets. Actual timing may vary depending on UART data
processing, I2C communication and display updates.
________________________________________

## Hardware Components

This project uses a Raspberry Pi Pico W microcontroller to collect
GPS position data and measurements from an IMU sensor.
The measured values are displayed on an OLED screen.
### Bill of Materials (BOM)

| No. | Component | Model | Quantity | Purpose |
|-----|-----------|-------|----------|---------|
| 1 | Microcontroller | Raspberry Pi Pico W | 1 | Main control unit |
| 2 | GPS Module | u-blox NEO-6M | 1 | GPS position and speed |
| 3 | Gyroscope & Accelerometer | MPU-6050 (GY-521) | 1 | Angular velocity and acceleration |
| 4 | OLED Display | SSD1306 (I2C, 128x64) | 1 | Displaying measured data |
| 5 | Pressure Sensor (Optional) | BMP280 / BME280 | 1 | Atmospheric pressure measurement |
| 6 | Breadboard | 400/830 tie-points | 1 | Prototype assembly |
| 7 | Jumper Wires | Dupont | 1 set | Electrical connections |
| 8 | USB Cable | Micro-USB | 1 | Power supply and programming |
| 9 | Button | Unknown | 1 | Switching between screen modes |

________________________________________

## Communication Interfaces

| Component | Interface | Pico W Pins |
|-----------|-----------|-------------|
| GPS NEO-6M | UART0 | GP0 (TX), GP1 (RX) |
| IMU MPU-6050 | I2C0 | GP4 (SDA), GP5 (SCL) |
| OLED SSD1306 | I2C0 | GP4 (SDA), GP5 (SCL) |
The IMU sensor and OLED display share the same I2C bus.
________________________________________

## Pin Connections

### GPS NEO-6M

-	GPS TX -> Pico GP1 (UART0 RX)
-	GPS RX -> Pico GP0 (UART0 TX)
-	GPS VCC -> Compatible power supply
-	GPS GND -> Pico GND

## IMU MPU-6050

-	VCC -> Pico 3V3
-	GND -> Pico GND
-	SDA -> Pico GP4
-	SCL -> Pico GP5

## OLED SSD1306

-	VCC -> Pico 3V3
-	GND -> Pico GND
-	SDA -> Pico GP4
-	SCL -> Pico GP5
________________________________________

## Power Supply

-	Raspberry Pi Pico W: 5 V via USB
-	IMU MPU-6050: 3.3 V
-	OLED SSD1306: 3.3 V
-	GPS NEO-6M: According to module specifications
-	Common GND for all components
________________________________________

## Software

-	**Programming Language:** MicroPython
-	**Development Environment:** Thonny / Visual Studio Code
-	**Version Control:** Git / GitHub
________________________________________

## Project Functionality

1.	Receive GPS data via UART.
2.	Check GPS fix status.
3.	Read acceleration and angular velocity from IMU.
4.  Process sensor data using Raspberry Pi Pico W.
5.	Display GPS and IMU measurements on OLED.
6.	Indicate unavailable or invalid GPS data.
________________________________________

## Schematic

![Schematic](Schema/Schema10.png)
________________________________________

## Hardware Component Testing

###  1.  MPU - 6050 - Gyroscope and Accelerometer

The MPU-6050 was successfully tested using
Raspberry Pi Pico W and MicroPython.

Acceleration and angular velocity data were
successfully measured using I2C communication.

**Test Status:** Successful

-	[MPU-6050 Documentation](test%20codes/MPU6050.md)
-	[MPU-6050 test code](test%20codes/MPU6050.py)

________________________________________

###  2.  NEO - 6M Module

The NEO-6M GPS module will be connected to the
Raspberry Pi Pico W using the UART0 interface.

The module will be used to receive GPS coordinates,
speed and satellite fix status.

The test will verify UART communication, NMEA data
reception and GPS fix validity.

**Test Status:** Successful

-	[NEO-6M Documentation](test%20codes/NEO-6M.md)
-	[NEO-6M test code](test%20codes/NEO-6M.py)
________________________________________

###  3.  SSD1306 – OLED Display

The SSD1306 OLED display will be connected to the
Raspberry Pi Pico W using the I2C0 interface.

The display will be used to show GPS coordinates,
speed, Wifi connection, GPS fix status and IMU measurements.

The test will verify I2C communication, text
rendering and display updates using MicroPython.

**Test Status:** Successful

-	[OLED Documentation](test%20codes/oled.md)
-	[OLED test code](test%20codes/oled.py)


##  System Integration

###  Integration of GPS, IMU and OLED Display

During the third week, the individually tested hardware components are being integrated into a single system controlled by the Raspberry Pi Pico W.
The main application is developed in MicroPython and combines three hardware modules:

-	**MPU-6050:** Measures acceleration and angular velocity using I2C communication.
-	**NEO-6M GPS:** Provides GPS coordinates, speed and satellite fix status using UART communication.
-	**SSD1306 OLED:** Displays the processed GPS and IMU measurements using I2C communication.
________________________________________

###  Software Integration

Each component is implemented as a separate software module to simplify testing, maintenance and integration.
The main application is responsible for:

1.	Initializing all connected hardware modules.
2.	Reading GPS and IMU sensor data.
3.	Processing and validating the received measurements.
4.	Displaying selected information on the OLED screen.
5.	Handling unavailable GPS data and communication errors.

###  Main Application

The main program combines the individual modules into one application.

**Main Python Code:** [main.py](LINK_TO_MAIN_CODE)
________________________________________

##  System Verification

###  Objective

The objective of the fourth week is to verify the
functionality, reliability and timing of the integrated
GPS and IMU Sensor Unit.

The system combines GPS navigation, inertial measurements,
Wi-Fi connectivity and an interactive OLED user interface
on the Raspberry Pi Pico W.

###  Implemented System Features

-	GPS data acquisition and processing.
-	Three-axis acceleration and angular velocity measurement.
-	Automatic gyroscope calibration.
-	GPS-based navigation and altitude processing.
-	OLED visualization of sensor and navigation data.
-	Manual display mode switching using GPIO17.
- Wi-Fi connection monitoring.
-	Wi-Fi signal strength indication.
-	Automatic Wi-Fi reconnection attempts.
-	Automatic MPU-6050 reconnection and recalibration.
-	GPS data freshness monitoring.
-	Controlled system shutdown.

###  Software Architecture

The application uses a modular software architecture.

| Module | Function |
|--------|----------|
| `main.py` | System initialization, task scheduling and integration. |
| `gyros_lib.py` | MPU-6050 initialization, calibration and measurements. |
| `gps_lib.py` | GPS communication and data processing. |
| `oled_lib.py` | OLED visualization and navigation interface. |
| `wifi_utils.py` | Wi-Fi connection and disconnection management. |
| `config.py` | Wi-Fi configuration parameters. |

###  Functional Verification

The following tests are used to verify the integrated
system functionality.

| Test | Expected Result | Status |
|------|-----------------|--------|
| System initialization | All available modules initialize correctly. | Pending |
| IMU calibration | Gyroscope offsets are calculated. | Pending |
| IMU measurement | Acceleration and angular velocity respond to movement. | Pending |
| GPS reception | Incoming GPS data is processed correctly. | Pending |
| GPS fix | Valid navigation data becomes available. | Pending |
| GPS timeout | Outdated GPS data is identified. | Pending |
| OLED visualization | Sensor and navigation data are displayed correctly. | Pending |
| Button control | Display mode changes after pressing the button. | Pending |
| Wi-Fi connection | The device connects to the configured network. | Pending |
| Wi-Fi signal indication | Signal strength is displayed correctly. | Pending |
| Wi-Fi disconnection | The Wi-Fi icon starts blinking. | Pending |
| Wi-Fi reconnection | The system attempts to restore the connection. | Pending |
| IMU reconnection | The sensor is reinitialized and recalibrated. | Pending |
| System stability | The application operates without unexpected interruption. | Pending |

###  Error Handling and Recovery

The application includes mechanisms designed to improve
system reliability:

-	IMU communication errors are detected and reported.
-	Unavailable IMU measurements are cleared.
-	Disconnected IMU sensors are periodically reinitialized.
-	Wi-Fi connection errors are reported.
-	Wi-Fi reconnection is attempted automatically.
-	GPS data freshness is monitored using a timeout.
-	Button input is protected by software debouncing.

###  Final Integrated Application

The main application coordinates all software modules
and manages communication between the hardware components.

**Main Python Code:** [main.py](LINK_TO_MAIN_CODE)

###  Verification Conclusion

The integrated application includes sensor measurements,
navigation processing, Wi-Fi monitoring and an interactive
display interface.

Final verification results will be documented after
completion of the hardware testing.




















