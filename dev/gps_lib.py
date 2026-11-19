# GPS library, contains code to initialize, read, parse and hand over GPS data from the NEO-6M
# All the data is included in gps_data and updated whenever update() is called
# Included is a simple has_fix() function which quickly says if we have a fix or not

from machine import UART
import time

gps = UART(0, baudrate=9600, tx=0, rx=1, rxbuf=2048)

buffer = b""

gps_data = {
    "latitude": None,
    "longitude": None,
    "altitude": None,
    "fix_quality": None,
    "fix_mode": None,
    "status": None,
    "satellites": None,
    "satellites_used": [],
    "satellites_in_view": None,
    "hdop": None,
    "vdop": None,
    "pdop": None,
    "speed_knots": None,
    "speed_kmh": None,
    "course": None,
    "time": None,
    "date": None,
    "last_sentence": None,
    "last_update": None
}

def to_float(value):
    try:
        return float(value) if value else None
    except ValueError:
        return None


def to_int(value):
    try:
        return int(value) if value else None
    except ValueError:
        return None


def convert_coordinate(value, direction):
    """
    Convert NMEA coordinate ddmm.mmmm to decimal degrees.
    """
    if not value or not direction:
        return None

    try:
        degrees = int(float(value) / 100)
        minutes = float(value) - degrees * 100

        decimal = degrees + minutes / 60

        if direction in ("S", "W"):
            decimal = -decimal

        return decimal

    except ValueError:
        return None


def checksum_valid(sentence):
    if "*" not in sentence:
        return False

    try:
        data, checksum = sentence.split("*", 1)

        calculated = 0

        for char in data[1:]:
            calculated ^= ord(char)

        return calculated == int(checksum[:2], 16)

    except (ValueError, IndexError):
        return False


def parse_nmea(sentence, gps_data):

    sentence = sentence.strip()

    if not sentence.startswith("$"):
        return False

    if not checksum_valid(sentence):
        return False

    data = sentence[1:sentence.index("*")]
    fields = data.split(",")

    sentence_type = fields[0][-3:]

    # GGA
    if sentence_type == "GGA":

        updates = {
            "time": fields[1],
            "latitude": convert_coordinate(fields[2], fields[3]),
            "longitude": convert_coordinate(fields[4], fields[5]),
            "fix_quality": to_int(fields[6]),
            "satellites": to_int(fields[7]),
            "hdop": to_float(fields[8]),
            "altitude": to_float(fields[9])
        }

    # RMC
    elif sentence_type == "RMC":

        updates = {
            "time": fields[1],
            "status": fields[2],
            "latitude": convert_coordinate(fields[3], fields[4]),
            "longitude": convert_coordinate(fields[5], fields[6]),
            "speed_knots": to_float(fields[7]),
            "course": to_float(fields[8]),
            "date": fields[9]
        }

    # GLL
    elif sentence_type == "GLL":

        updates = {
            "latitude": convert_coordinate(fields[1], fields[2]),
            "longitude": convert_coordinate(fields[3], fields[4]),
            "time": fields[5],
            "status": fields[6]
        }

    # GSA
    elif sentence_type == "GSA":

        updates = {
            "fix_mode": to_int(fields[2]),
            "satellites_used": [
                value for value in fields[3:15] if value
            ],
            "pdop": to_float(fields[15]),
            "hdop": to_float(fields[16]),
            "vdop": to_float(fields[17])
        }

    # GSV
    elif sentence_type == "GSV":

        updates = {
            "satellites_in_view": to_int(fields[3])
        }

    # VTG
    elif sentence_type == "VTG":

        updates = {
            "course": to_float(fields[1]),
            "speed_knots": to_float(fields[5]),
            "speed_kmh": to_float(fields[7])
        }

    else:
        return False

    # Update only the fields belonging to this sentence
    for key, value in updates.items():
        gps_data[key] = value

    gps_data["last_sentence"] = sentence_type
    gps_data["last_update"] = time.ticks_ms()

    return True


def update():

    global buffer

    # Check if data is available
    if not gps.any():
        return 0

    # Read all currently available UART data
    incoming = gps.read()

    if not incoming:
        return 0

    buffer += incoming

    sentences_processed = 0

    # Process complete lines
    while b"\n" in buffer:

        line, buffer = buffer.split(b"\n", 1)

        try:
            sentence = line.decode("ascii").strip()

            if parse_nmea(sentence, gps_data):
                sentences_processed += 1

        except (UnicodeError, ValueError, IndexError):
            pass

    return sentences_processed


def get_data():
    return gps_data.copy()


def has_fix():
    return (
        gps_data["fix_quality"] is not None
        and gps_data["fix_quality"] > 0
    )
