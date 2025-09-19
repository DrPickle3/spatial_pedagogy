import time
import re
import matplotlib.pyplot as plt
import socket
import json
import csv
import numpy as np
from scipy.optimize import minimize

TCP_IP = "0.0.0.0"
TCP_PORT = 5000

anchors = {
    "AAA1": (0.0, 0.0, 0.0),
    "AAA2": (0.0, 0.0, 0.0),
    "AAA3": (0.0, 0.0, 0.0),
    "AAA4": (0.0, 0.0, 0.0),
    "AAA5": (0.0, 0.0, 0.0),
    "AAA6": (0.0, 0.0, 0.0),
    "AAA7": (0.0, 0.0, 0.0),
}

filename = "../logs/positions.csv"
positions = []

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((TCP_IP, TCP_PORT))
sock.listen(1)

with open(filename, "w", newline="") as file:  # clear file
    writer = csv.writer(file)
    writer.writerow(["x"])

def read_data(conn):
    global buffer
    try:
        # Read new data
        chunk = conn.recv(1024).decode("utf-8")
        buffer += chunk

        uwb_list = []

        # Use regex to extract complete JSON objects
        pattern = r'\{"links":\s*\[.*?\]\}'

        matches = re.findall(pattern, buffer)

        if not matches:
            return uwb_list  # nothing complete yet

        # Keep only the last complete JSON object
        last_json = matches[-1]

        # Remove everything up to and including last complete JSON
        last_index = buffer.rfind(last_json) + len(last_json)
        buffer = buffer[last_index:]

        # Parse it
        uwb_data = json.loads(last_json)
        uwb_list = uwb_data.get("links", [])

        return uwb_list

    except json.JSONDecodeError as e:
        print("EXCEPTION!", e, last_json if 'last_json' in locals() else buffer)
        return []
    except Exception as e:
        print("EXCEPTION!", e)
        return []


def tag_pos(ranges, anchors):
    keys = [k for k in ranges if k in anchors]
    dists = np.array([ranges[k] for k in keys])

    return dists[0]

def update_scatter_1d():
    if not positions:
        return
    plt.clf()

    xs = positions  

    plt.scatter(xs, [0]*len(xs), c="blue", s=20, alpha=0.6, label="Tag positions")

    plt.xlabel("X (m)")
    plt.yticks([])  # hide Y axis ticks
    plt.title("Nuage de points 1D - Précision de localisation")
    plt.legend()
    plt.grid(True, axis="x")  # only vertical grid lines
    plt.pause(0.01)

def main():

    while True:
        print(f"***Waiting for connection on port {TCP_PORT}***")
        conn, addr = sock.accept()
        print(f"***Connection accepted from {addr}***")

        global buffer
        buffer = ""  # reset buffer per connection

        try:
            while True:
                list = read_data(conn)  # pass `conn` instead of global `data`
                ranges = {}

                for one in list:
                    if one["A"] in anchors:
                        ranges[one["A"]] = float(one["R"])
                        ax, ay, az = anchors[one["A"]]

                if len(ranges) >= 1:
                    x = tag_pos(ranges, anchors)
                    with open(filename, "a", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow([x])
                    
                    if x > 0.01:
                        positions.append(x)
                    update_scatter_1d()

                time.sleep(0.1)

        except (ConnectionResetError, BrokenPipeError):
            print(f"***Connection lost from {addr}, waiting for new device...***")
            continue



if __name__ == '__main__':
    main()
