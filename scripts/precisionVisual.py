import time
import re
import turtle
import utils
import socket
import json
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

TCP_IP = "0.0.0.0"
TCP_PORT = 5000
#tag : 0.9652, 1.4224       2D: (1.06, 1.30)
# anchors = {
#     "AAA1": (0.0, 0.0, 1.651),
#     "AAA2": (0.7874, 2.667, 1.6764),
#     "AAA3": (3.2766, 1.3716, 0.7366),
#     "AAA4": (3.2766, 0.1524, 0.7366),
# }
anchors = {
    "AAA1": (1.397, 0.0, 0.0),
    "AAA2": (0.0, 0.0, 0.0),
    "AAA3": (0.0, 0.0, 0.0),
    "AAA4": (0.0, 0.0, 0.0),
}

filename = "../logs/positions.csv"

positions = []
distance_a1_a2 = 1.397

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((TCP_IP, TCP_PORT))
sock.listen(1)

with open(filename, "w", newline="") as file:  # clear file
    writer = csv.writer(file)
    writer.writerow(["x", "y"])

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
    anchor_coords = np.array([anchors[k] for k in keys])
    dists = np.array([ranges[k] for k in keys])

    def error(pos):
        est = np.sqrt(((anchor_coords - pos) ** 2).sum(axis=1))
        return np.sum((est - dists) ** 2)

    result = minimize(error, x0=np.mean(anchor_coords, axis=0))
    return float(result.x[0]), float(result.x[1])

def update_scatter():
    if not positions:
        return
    plt.clf()
    xs, ys = zip(*positions)
    plt.scatter(xs, ys, c="blue", s=20, alpha=0.6, label="Tag positions")
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title("Nuage de points 2D - Précision de localisation")
    plt.legend()
    plt.grid(True)
    plt.pause(0.01)

def main():
    screen = turtle.Screen()
    screen.setup(1200, 800)
    screen.tracer(True)

    t_ui = turtle.Turtle()
    t_anchors = turtle.Turtle()
    t_tag = turtle.Turtle()
    utils.turtle_init(t_ui)
    utils.turtle_init(t_anchors)
    utils.turtle_init(t_tag)

    while True:
        print(f"***Waiting for connection on port {TCP_PORT}***")
        conn, addr = sock.accept()
        print(f"***Connection accepted from {addr}***")

        global buffer
        buffer = ""  # reset buffer per connection

        try:
            while True:
                list = read_data(conn)
                ranges = {}

                utils.clean(t_anchors)

                for one in list:
                    if one["A"] in anchors:
                        ranges[one["A"]] = float(one["R"])
                        ax, ay, az = anchors[one["A"]]
                        pos_x = -250 + ax * utils.meter2pixel
                        pos_y = 150 - ay * utils.meter2pixel
                        utils.draw_uwb_anchor(pos_x, pos_y, one["A"], t_anchors)

                if len(ranges) >= 2:
                    x, y = tag_pos(ranges, anchors)
                    with open(filename, "a", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow([x, y])

                    if x > 0.1 and y > 0.1:
                        positions.append((x, y))
                    update_scatter()

                    utils.clean(t_tag)
                    utils.draw_uwb_tag(x, y, "TAG", t_tag)

                time.sleep(0.1)

        except (ConnectionResetError, BrokenPipeError):
            print(f"***Connection lost from {addr}, waiting for new device...***")
            continue

    turtle.mainloop()


if __name__ == '__main__':
    main()