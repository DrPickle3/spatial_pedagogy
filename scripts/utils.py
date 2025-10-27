import csv
import datetime
import json
import matplotlib.pyplot as plt
import numpy as np
import re
from scipy.optimize import minimize
import socket
import turtle
from zeroconf import ServiceInfo, Zeroconf

TCP_IP = "0.0.0.0"
TCP_PORT = 5000

bin_size = 0.3  # Taille des cases de l'hisogramme dans matplotlib en metres
meter2pixel = 200
true_pos = None

# anchors = {
#     "AAA1": (0.0, 2.4892, 1.1176),#        sur ordi
#     "AAA2": (2.9972, 0.5588, 2.032),#  porte chambre
#     "AAA3": (0.0, 0.0, 0.0),
#     "AAA4": (0.0, 0.0, 1.1176),#       coin du lit
#     "AAA5": (0.0, 0.0, 0.0),
#     "AAA6": (0.0, 0.0, 0.0),
#     "AAA7": (2.9972, 2.7432, 1.8796),# garde-robe
# }

# anchors = {
#     "AAA1": (0.0, 0.0, 0.0),
#     "AAA2": (0.0, 0.0, 1.4986),        # bureau metal
#     "AAA3": (3.175, 0.0, 0.7366),      # coin bureau fenetre
#     "AAA4": (3.175, 1.4478, 0.7366),   # a cote de lordi
#     "AAA5": (0.0, 0.0, 0.0),
#     "AAA6": (0.0, 0.0, 0.0),
#     "AAA7": (0.889, 2.6924, 1.524),    # mur de metal
# }

anchors = {
    "AAA1": (0.0, 0.0, 0.0),
    "AAA2": (0.0, 0.0, 1.0),
    "AAA3": (0.0, 0.0, 0.0),
    "AAA4": (0.0, 0.0, 0.0),
    "AAA5": (0.0, 0.0, 0.0),
    "AAA6": (2.921, 0.0, 1.0),
    "AAA7": (0.0, 0.0, 0.0),
}

filename = "../logs/positions.csv"

positions = []


def update_scatter(real_pos=None):
    if not positions:
        return

    plt.clf()

    xs = np.array([p[0] for p in positions])
    ys = np.array([p[1] for p in positions])

    anchor_xs = [coord[0] for coord in anchors.values()]
    anchor_ys = [coord[1] for coord in anchors.values()]

    all_x = np.concatenate([xs, anchor_xs])
    all_y = np.concatenate([ys, anchor_ys])

    # --- Compute dynamic limits with padding ---
    padding = 1  # meter
    x_min, x_max = all_x.min() - padding, all_x.max() + padding
    y_min, y_max = all_y.min() - padding, all_y.max() + padding

    x_bins = int(np.ceil((x_max - x_min) / bin_size))
    y_bins = int(np.ceil((y_max - y_min) / bin_size))

    # --- 2D histogram (density grid) ---
    counts, xedges, yedges, im = plt.hist2d(
        xs, ys,
        bins=[x_bins, y_bins],
        range=[[x_min, x_max],
        [y_min, y_max]],
        cmap='Blues',
        alpha=0.7
    )

    # --- Add scatter of points ---
    plt.scatter(xs, ys, c="red", s=10, alpha=0.6, label="Mesures individuelles")

    # --- Compute and show centroid (mode-like precision center) ---
    centroid_x, centroid_y = np.mean(xs), np.mean(ys)
    plt.scatter(
        centroid_x, centroid_y, c="orange", s=80, marker="x",
        label=f"Centre ≈ ({centroid_x:.2f}, {centroid_y:.2f})"
    )

    # Plot anchors in red with a different marker
    plt.scatter(anchor_xs, anchor_ys, c="purple", s=80, marker="X", label="Anchors")

    # --- Add real position reference, if provided ---
    if real_pos is not None:
        plt.scatter(
            real_pos[0], real_pos[1], c="green", s=100, marker="*",
            label=f"Position réelle ({real_pos[0]:.2f}, {real_pos[1]:.2f})"
        )

    # --- Formatting ---
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    plt.title("Carte de précision 2D des mesures")
    plt.colorbar(im, label="Nombre de mesures")
    plt.xlim(x_min, x_max)
    plt.ylim(y_min, y_max)
    plt.gca().invert_yaxis()
    plt.legend()
    plt.grid(True, linestyle=":")
    plt.pause(0.01)

    return plt


def on_exit(scatter_filename):
    if scatter_filename:
        update_scatter(true_pos).savefig(scatter_filename)
    plt.close('all')


def main_loop(sock, scatter_filename = "", display = False):
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

            if len(ranges) >= 2:
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
        on_exit(scatter_filename)
        conn.close()
        raise KeyboardInterrupt


def tag_pos(ranges, anchors):
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
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Nb Anchors", "id_1", "id_2", "id_3", "id_4", "d1", "d2", "d3",
            "d4", "pos_x", "pos_y", "Timestamp"            
        ])


def screen_init():
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
    pass


def clean(t=turtle):
    t.clear()


def draw_ui(t):
    write_txt(-300, 250, "UWB Positon", "black",  t, f=('Arial', 32, 'normal'))
    fill_rect(-400, 200, 800, 40, "black", t)
    write_txt(-50, 205, "WALL", "yellow",  t, f=('Arial', 24, 'normal'))


def draw_uwb_anchor(x, y, txt, t):
    r = 20
    fill_cycle(x, y, r, "green", t)
    write_txt(x + r, y, txt,
              "black",  t, f=('Arial', 16, 'normal'))


def draw_uwb_tag(x, y, txt, t):
    pos_x = -250 + int(x * meter2pixel)
    pos_y = 150 - int(y * meter2pixel)
    r = 20
    fill_cycle(pos_x, pos_y, r, "blue", t)
    write_txt(pos_x, pos_y, txt + ": (" + str(x) + "," + str(y) + ")",
              "black",  t, f=('Arial', 16, 'normal'))
