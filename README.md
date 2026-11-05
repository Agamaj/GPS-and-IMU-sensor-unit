# GPS and IMU Sensor Unit

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
**Important:** Verify the GPS module supply voltage
and UART logic levels before connecting it.
All Pico W GPIO signals must be 3.3 V compatible.
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
4.	Process sensor data using Raspberry Pi Pico W.
5.	Display GPS and IMU measurements on OLED.
6.	Indicate unavailable or invalid GPS data.
________________________________________

## Project Progress

### Week 1 - Proposal and Architecture

-	[x] Preliminary component selection
-	[x] Communication interface selection
-	[x] Initial pin assignment
-	[ ] Hardware verification
-	[ ] Block diagram approval
-	[ ] Timing and concurrency plan
