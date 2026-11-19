
import uasyncio as asyncio
import gps_lib
import time


# ==========================================
# CONFIGURATION
# ==========================================

GPS_UPDATE_INTERVAL = 10       # milliseconds
MAIN_LOOP_INTERVAL = 20        # milliseconds
GPS_PRINT_INTERVAL = 1000      # milliseconds


# ==========================================
# GPS TASK
# ==========================================

async def gps_task():

    print("GPS task started")

    while True:

        # Read and process available GPS data
        gps_lib.update()

        # Yield control to other tasks
        await asyncio.sleep_ms(GPS_UPDATE_INTERVAL)


# ==========================================
# IMU TASK (PLACEHOLDER)
# ==========================================

async def imu_task():

    print("IMU task started")

    while True:

        # TODO:
        # Read IMU sensors
        # Process accelerometer data
        # Process gyroscope data

        await asyncio.sleep_ms(10)


# ==========================================
# MAIN APPLICATION TASK
# ==========================================

async def main_task():

    print("Main application started")

    last_gps_print = time.ticks_ms()

    while True:

        # Get a snapshot of the latest GPS data
        gps_data = gps_lib.get_data()

        # Check GPS fix
        if gps_lib.has_fix():

            latitude = gps_data["latitude"]
            longitude = gps_data["longitude"]
            altitude = gps_data["altitude"]

            # TODO:
            # Use GPS data
            # Combine with IMU data
            # Perform calculations

        else:
            # No valid GPS fix
            pass

        # Periodically print GPS information
        now = time.ticks_ms()

        if time.ticks_diff(now, last_gps_print) >= GPS_PRINT_INTERVAL:

            if gps_lib.has_fix():
                print("GPS FIX:")
                print("Latitude:", gps_data["latitude"])
                print("Longitude:", gps_data["longitude"])
                print("Altitude:", gps_data["altitude"])
                print("Satellites:", gps_data["satellites"])

            else:
                print("Waiting for GPS fix...")

            last_gps_print = now

        # Yield control
        await asyncio.sleep_ms(MAIN_LOOP_INTERVAL)


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================

async def main():

    print("Starting GPS and IMU sensor unit...")

    # Start independent tasks
    asyncio.create_task(gps_task())
    asyncio.create_task(imu_task())

    # Run main application
    await main_task()


# ==========================================
# START PROGRAM
# ==========================================

try:
    asyncio.run(main())

except KeyboardInterrupt:
    print("Program stopped")
