import time
import re
import turtle
import socket
import socketserver
from zeroconf import ServiceInfo, Zeroconf
import json
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

TCP_IP = "0.0.0.0"
TCP_PORT = 5000
#tag : 0.9652, 1.4224       2D: (1.06, 1.30)
anchors = {
    "AAA1": (0.0, 2.4892, 1.1176),#        sur ordi
    "AAA2": (2.9972, 0.5588, 2.032),#  porte chambre
    "AAA3": (0.0, 0.0, 0.0),
    "AAA4": (0.0, 0.0, 1.1176),#       coin du lit
    "AAA5": (0.0, 0.0, 0.0),
    "AAA6": (0.0, 0.0, 0.0),
    "AAA7": (2.9972, 2.7432, 1.8796),# garde-robe
}

filename = "../logs/positions.csv"

positions = []

hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

info = ServiceInfo(
    "_tcpserver._tcp.local.",             # service type
    "spatialPedagogy._tcpserver._tcp.local.", # service name
    addresses=[socket.inet_aton(local_ip)],
    port=TCP_PORT,
    properties={},
    server=f"spatialPedagogy.local."
)

zeroconf = Zeroconf()
zeroconf.register_service(info)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((TCP_IP, TCP_PORT))
sock.listen(1)

meter2pixel = 200

with open(filename, "w", newline="") as file:  # clear file
    writer = csv.writer(file)
    writer.writerow(["x", "y"])


def turtle_init(t=turtle):
    t.hideturtle()
    t.speed(0)


def fill_cycle(x, y, r, color="black", t=turtle):
    t.up()
    t.goto(x, y)
    t.down()
    t.dot(r, color)
    t.up()


def write_txt(x, y, txt, color="black", t=turtle, f=('Arial', 12, 'normal')):
    t.pencolor(color)
    t.up()
    t.goto(x, y)
    t.down()
    t.write(txt, move=False, align='left', font=f)
    t.up()


def draw_rect(x, y, w, h, color="black", t=turtle):
    t.pencolor(color)
    t.up()
    t.goto(x, y)
    t.down()
    t.goto(x + w, y)
    t.goto(x + w, y + h)
    t.goto(x, y + h)
    t.goto(x, y)
    t.up()


def fill_rect(x, y, w, h, color=("black", "black"), t=turtle):
    t.begin_fill()
    draw_rect(x, y, w, h, color, t)
    t.end_fill()


def clean(t=turtle):
    t.clear()


def draw_ui(t):
    write_txt(-300, 250, "UWB Position", "black", t, f=('Arial', 32, 'normal'))
    fill_rect(-400, 200, 800, 40, "black", t)
    write_txt(-50, 205, "WALL", "yellow", t, f=('Arial', 24, 'normal'))


def draw_uwb_anchor(x, y, txt, t):
    r = 20
    fill_cycle(x, y, r, "green", t)
    write_txt(x + r, y, txt, "black", t, f=('Arial', 16, 'normal'))


def draw_uwb_tag(x, y, txt, t):
    pos_x = -250 + int(x * meter2pixel)
    pos_y = 150 - int(y * meter2pixel)
    r = 20
    fill_cycle(pos_x, pos_y, r, "blue", t)
    write_txt(pos_x, pos_y, f"{txt}: ({x:.2f},{y:.2f})",
              "black", t, f=('Arial', 16, 'normal'))

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
    
    # Plot tag positions
    xs, ys = zip(*positions)
    plt.scatter(xs, ys, c="blue", s=20, alpha=0.6, label="Tag positions")

    # Plot anchors in red with a different marker
    anchor_xs = [coord[0] for coord in anchors.values()]
    anchor_ys = [coord[1] for coord in anchors.values()]
    plt.scatter(anchor_xs, anchor_ys, c="red", s=80, marker="X", label="Anchors")

    # Set plot limits with margin
    margin = 0.5
    xmin, xmax = min(anchor_xs) - margin, max(anchor_xs) + margin
    ymin, ymax = min(anchor_ys) - margin, max(anchor_ys) + margin
    plt.xlim(xmin, xmax)
    plt.ylim(ymin, ymax)

    plt.gca().invert_yaxis()

    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title("Nuage de points 2D - Précision de localisation")
    plt.legend()
    plt.grid(True)
    plt.pause(0.1)



def main():
    screen = turtle.Screen()
    screen.setup(1200, 800)
    screen.tracer(True)

    t_ui = turtle.Turtle()
    t_anchors = turtle.Turtle()
    t_tag = turtle.Turtle()
    turtle_init(t_anchors)
    turtle_init(t_tag)

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

                clean(t_anchors)

                for one in list:
                    if one["A"] in anchors:
                        ranges[one["A"]] = float(one["R"])
                        ax, ay, az = anchors[one["A"]]
                        pos_x = -250 + ax * meter2pixel
                        pos_y = 150 - ay * meter2pixel
                        draw_uwb_anchor(pos_x, pos_y, one["A"], t_anchors)

                if len(ranges) >= 2:
                    x, y = tag_pos(ranges, anchors)
                    with open(filename, "a", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow([x, y])

                    if x > 0.1 and y > 0.1:
                        positions.append((x, y))
                    # update_scatter()

                    clean(t_tag)
                    draw_uwb_tag(x, y, "TAG", t_tag)

                time.sleep(0.1)

        except (ConnectionResetError, BrokenPipeError):
            print(f"***Connection lost from {addr}, waiting for new device...***")
            continue

    turtle.mainloop()


if __name__ == '__main__':
    main()
