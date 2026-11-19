from machine import UART
import time
# Works standalone without the original NEO-6M.py file

# -------------------------------
# Directionary definition
# -------------------------------

gps_data = {
    # Position
    "latitude": None,
    "longitude": None,
    "altitude": None,
    
    # GPS fix
    "fix_quality": None,
    "fix_mode": None,
    "status": None,

    # Satellites
    "satellites": None,
    "satellites_used": [],
    "satellites_in_view": None,

    # Accuracy
    "hdop": None,
    "vdop": None,
    "pdop": None,

    # Movement
    "speed_knots": None,
    "speed_kmh": None,
    "course": None,

    # Time
    "time": None,
    "date": None,

    # Communication
    "last_sentence": None,
    "last_update": None
}

# -------------------------------
# UART CONFIGURATION
# -------------------------------

gps = UART(0, baudrate=9600, tx=0, rx=1)

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------

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


# -------------------------------
# NMEA CHECKSUM
# -------------------------------

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


# -------------------------------
# NMEA SENTENCE PARSER
# -------------------------------


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

# -------------------------------
# UART LINE READER
# -------------------------------

buffer = b""

print("NEO-6M GPS parser started")

while True:

    if gps.any():

        data = gps.read()

        if data:
            buffer += data

            while b"\n" in buffer:

                line, buffer = buffer.split(b"\n", 1)

                try:
                    sentence = line.decode("ascii").strip()

                    if parse_nmea(sentence, gps_data):
                        print(gps_data)

                except (UnicodeError, ValueError):
                    pass

    time.sleep_ms(10)