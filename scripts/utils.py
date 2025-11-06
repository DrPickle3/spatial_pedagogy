import csv
import datetime
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import re
from scipy.optimize import minimize
import socket
import turtle
from zeroconf import ServiceInfo, Zeroconf

TCP_IP = "0.0.0.0"
TCP_PORT = 5000

meter2pixel = 200

filename = "../logs/positions.csv"

minimum_anchors_for_position = 4


def load_anchors(config_path="../config.json"):
    """ Load anchors from a JSON configuration file. """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        data = json.load(f)

    global anchors
    anchors = {k: tuple(v) for k, v in data["anchors"].items()}
    return anchors


def on_exit():
    """ Close all matplotlib plots on exit """
    plt.close('all')


def main_loop(sock, display = False):
    """ Main loop handling TCP data reception and visualization """
    print(f"***Waiting for connection on port {TCP_PORT}***")
    conn, addr = sock.accept()
    conn.settimeout(5.0)
    print(f"***Connection accepted from {addr}***")

    if display:
        global t_ui, t_anchors, t_tag
    buffer = ""  # reset buffer per connection

    try:
        while True:
            anchors_list, buffer = read_data(conn, buffer)
            ranges = {}

            if display:
                clean(t_anchors)

            for anchor in anchors_list:
                if anchor["A"] in anchors:
                    anchor_range = float(anchor["R"])
                    if anchor_range > 0.0 and anchor_range < 10.0:
                        ranges[anchor["A"]] = anchor_range
                    if display:
                        ax, ay, az = anchors[anchor["A"]]
                        pos_x = -250 + ax * meter2pixel
                        pos_y = 150 - ay * meter2pixel
                        draw_uwb_anchor(pos_x, pos_y, anchor["A"], t_anchors)

            anchor_ids = sorted(ranges.keys())[:4]
            distances = [ranges[a] for a in anchor_ids]

            while len(anchor_ids) < 4:
                anchor_ids.append(None)
            while len(distances) < 4:
                distances.append(None)

            if len(ranges) >= minimum_anchors_for_position:
                x, y = tag_pos(ranges, anchors)

                if x != -1 and y != -1:

                    with open(filename, "a", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow([
                            len(ranges),
                            *anchor_ids,
                            *distances,
                            x, y, datetime.datetime.now()
                        ])
                    if display:
                        clean(t_tag)
                        draw_uwb_tag(x, y, "TAG", t_tag)

    except (ConnectionResetError, BrokenPipeError):
        print(f"***Connection lost from {addr}, waiting for new device...***")
        conn.close()
        raise ConnectionResetError
    except socket.timeout:
        conn.close()
        pass # to try again
    except KeyboardInterrupt:
        on_exit()
        conn.close()
        raise KeyboardInterrupt


def tag_pos(ranges, anchors):
    """ Compute tag position based on distances to known anchors """
    keys = [k for k in ranges if k in anchors]
    anchor_coords = np.array([anchors[k] for k in keys])
    dists = np.array([ranges[k] for k in keys])

    if len(dists) == 2:
        sorted_pairs = sorted(zip(anchor_coords, dists), key=lambda p: p[0][0])
        left_anchor, left_dist = sorted_pairs[0]
        right_anchor, right_dist = sorted_pairs[1]

        c = np.linalg.norm(right_anchor - left_anchor)
        return tag_pos_2_anchors(right_dist, left_dist, c)

    def error(pos):
        est = np.sqrt(((anchor_coords - pos) ** 2).sum(axis=1))
        return np.sum((est - dists) ** 2)

    result = minimize(error, x0=np.mean(anchor_coords, axis=0))
    return round(float(result.x[0]), 3), round(float(result.x[1]),3)


def tag_pos_2_anchors(a, b, c):
    """ Estimate 2D tag position using only 2 anchors """
    x=0.0
    y=0.0

    if (a != 0 and b != 0 and c != 0) :
        cos_a = (b * b + c * c - a * a) / (2 * b * c)
        if cos_a * cos_a > 1:
            return -1, -1
        x = b * cos_a
        sin_a = (1 - cos_a * cos_a) ** 0.5
        y = b * sin_a

    return round(x.real, 3), round(y.real, 3)


def connect_wifi():
    """ Setup a Wi-Fi TCP server using Zeroconf for discovery """

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
    return sock


def read_data(conn, buffer):
    """ Read and parse incoming JSON UWB data from the socket """
    try:
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

        return uwb_list, buffer

    except json.JSONDecodeError as e:
        print("EXCEPTION!", e, last_json if 'last_json' in locals() else buffer)
        return [], buffer
    except socket.timeout:
        print("Lost connection to the Tag")
        raise socket.timeout
    except Exception as e:
        print("EXCEPTION!", e)
        return [], buffer


def clear_file():
    """ Clear and reinitialize the CSV output file """
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Nb Anchors", "id_1", "id_2", "id_3", "id_4", "d1", "d2", "d3",
            "d4", "pos_x", "pos_y", "Timestamp"            
        ])


def screen_init():
    """ Initialize the turtle-based UI """
    screen = turtle.Screen()
    screen.setup(1200, 800)
    screen.tracer(True)

    global t_ui, t_anchors, t_tag

    t_ui = turtle.Turtle()
    t_anchors = turtle.Turtle()
    t_tag = turtle.Turtle()
    # turtle_init(t_ui) #(Wall)
    turtle_init(t_anchors)
    turtle_init(t_tag)


def turtle_init(t=turtle):
    """ Initialize a turtle object """
    t.hideturtle()
    t.speed(0)


def fill_cycle(x, y, r, color="black", t=turtle):
    """ Draw a filled circle on the screen """
    t.up()
    t.goto(x, y)
    t.down()
    t.dot(r, color)
    t.up()


def write_txt(x, y, txt, color="black", t=turtle, f=('Arial', 12, 'normal')):
    """ Write text at a given position """

    t.pencolor(color)
    t.up()
    t.goto(x, y)
    t.down()
    t.write(txt, move=False, align='left', font=f)
    t.up()


def draw_rect(x, y, w, h, color="black", t=turtle):
    """ Draw a rectangle """
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
    """ Fill a rectangle with color """
    t.begin_fill()
    draw_rect(x, y, w, h, color, t)
    t.end_fill()
    pass


def clean(t=turtle):
    """ Clear a turtle layer """
    t.clear()


def draw_ui(t):
    """ Draw main UI elements """
    write_txt(-300, 250, "UWB Positon", "black",  t, f=('Arial', 32, 'normal'))
    fill_rect(-400, 200, 800, 40, "black", t)
    write_txt(-50, 205, "WALL", "yellow",  t, f=('Arial', 24, 'normal'))


def draw_uwb_anchor(x, y, txt, t):
    """ Draw a UWB anchor point """
    r = 20
    fill_cycle(x, y, r, "green", t)
    write_txt(x + r, y, txt,
              "black",  t, f=('Arial', 16, 'normal'))


def draw_uwb_tag(x, y, txt, t):
    """ Draw the tag position """
    pos_x = -250 + int(x * meter2pixel)
    pos_y = 150 - int(y * meter2pixel)
    r = 20
    fill_cycle(pos_x, pos_y, r, "blue", t)
    write_txt(pos_x, pos_y, txt + ": (" + str(x) + "," + str(y) + ")",
              "black",  t, f=('Arial', 16, 'normal'))
