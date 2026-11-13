
import csv
import math
import sys

EARTH_RADIUS = 6371000


# --------------------------------
# 1. Haversine distance function
# --------------------------------

def haversine(lat1, lon1, lat2, lon2):

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    # Protect against floating-point rounding errors
    a = max(0.0, min(1.0, a))

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return EARTH_RADIUS * c


# --------------------------------
# 2. Read target coordinates
# --------------------------------

def read_targets(filename):

    targets = []

    with open(filename, "r", newline="", encoding="utf-8-sig") as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:
                target_number = int(row["target"])
                lat = float(row["lat"])
                lon = float(row["lon"])

                if not (-90 <= lat <= 90):
                    continue

                if not (-180 <= lon <= 180):
                    continue

                targets.append((target_number, lat, lon))

            except (ValueError, KeyError, TypeError):
                continue

    # Ensure targets are visited in the correct order
    targets.sort(key=lambda x: x[0])

    return targets


# --------------------------------
# 3. Main telemetry parser
# --------------------------------

def process_log(log_file, target_file):

    targets = read_targets(target_file)

    with open(log_file, "r", newline="", encoding="utf-8-sig") as file:

        reader = csv.DictReader(file)

        records = []

        for row in reader:

            try:
                time = int(row["time_s"])

                mode = row["mode"].strip().upper()

                lat = float(row["lat"])
                lon = float(row["lon"])

                if not math.isfinite(lat) or not math.isfinite(lon):
                    lat = None
                    lon = None

                elif not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    lat = None
                    lon = None

            except (ValueError, KeyError, TypeError):
                try:
                    time = int(row["time_s"])
                    mode = row.get("mode", "").strip().upper()
                except (ValueError, KeyError, TypeError):
                    continue

                lat = None
                lon = None

            records.append((time, mode, lat, lon))

    # Process records chronologically
    records.sort(key=lambda x: x[0])

    # Previous valid GPS reading
    prev_lat = None
    prev_lon = None
    prev_time = None

    # Current target
    target_index = 0

    # End of the five-second green period (exclusive)
    green_until = None

    # Process every available log record
    for time, mode, lat, lon in records:

        # Check whether the previous green period has ended
        if green_until is not None and time >= green_until:

            target_index += 1
            green_until = None

        # Calculate velocity if current GPS is valid
        speed = None

        if lat is not None and prev_time is not None:

            dt = time - prev_time

            if dt > 0:

                movement = haversine(
                    prev_lat, prev_lon,
                    lat, lon
                )

                speed = movement / dt

        # If green period is active, keep green
        if green_until is not None and time < green_until:

            light = "green"

        else:

            # Normal mode indicator
            light = "red" if mode == "AUTO" else "blue"

            # Check arrival conditions
            if (
                mode == "AUTO"
                and lat is not None
                and lon is not None
                and speed is not None
                and target_index < len(targets)
            ):

                _, target_lat, target_lon = targets[target_index]

                distance = haversine(
                    lat, lon,
                    target_lat, target_lon
                )

                if distance <= 3.0 and speed < 0.5:

                    light = "green"

                    # Green remains active for 5 seconds
                    green_until = time + 5

        # Print one line for each available log record
        print(f"{time},{light}")

        # Update previous valid GPS reading
        # Missing coordinates must not overwrite it
        if lat is not None and lon is not None:

            prev_lat = lat
            prev_lon = lon
            prev_time = time


# --------------------------------
# 4. Run the program
# --------------------------------

if __name__ == "__main__":

    if len(sys.argv) != 3:

        print("Usage: python light.py mission_log.csv targets.csv")

    else:

        process_log(sys.argv[1], sys.argv[2])
