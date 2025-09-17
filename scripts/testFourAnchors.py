import time
import re
import turtle
import socket
import json
import csv
import numpy as np
from scipy.optimize import minimize

TCP_IP = "0.0.0.0"
TCP_PORT = 5000
#tag : 0.9652, 1.4224       2D: (1.06, 1.30)
anchors = {
    "AAA1": (0.0, 0.0, 1.651),
    "AAA2": (0.7874, 2.667, 1.6764),
    "AAA3": (3.2766, 1.3716, 0.7366),
    "AAA4": (3.2766, 0.1524, 0.7366),
}

filename = "../logs/positions.csv"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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


def main():
    screen = turtle.Screen()
    screen.setup(1200, 800)
    screen.tracer(True)

    t_ui = turtle.Turtle()
    t_anchors = turtle.Turtle()
    t_tag = turtle.Turtle()
    turtle_init(t_ui)
    turtle_init(t_anchors)
    turtle_init(t_tag)

    draw_ui(t_ui)

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

                    clean(t_tag)
                    draw_uwb_tag(x, y, "TAG", t_tag)

                time.sleep(0.1)

        except (ConnectionResetError, BrokenPipeError):
            print(f"***Connection lost from {addr}, waiting for new device...***")
            continue

    turtle.mainloop()


if __name__ == '__main__':
    main()
