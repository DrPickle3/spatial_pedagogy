from collections import defaultdict

filename = "../logs/positions.csv"  # your CSV file

# store ranges per device
ranges = defaultdict(list)

with open(filename, "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        # example line: "from: AAA7 Range: 2.100 m RX power: 0 dBm"
        parts = line.split()
        device = parts[1]  # AAA7
        range_value = float(parts[3])  # 2.100
        ranges[device].append(range_value)

# compute averages
for device, values in ranges.items():
    avg = sum(values) / len(values)
    print(f"Device {device} average range = {avg:.3f} m over {len(values)} measures")
