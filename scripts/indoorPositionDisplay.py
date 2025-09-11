import time
import turtle
import socket
import json
import csv

TCP_IP = "0.0.0.0"
TCP_PORT = 5000

ANCHOR1 = "AAA1"
ANCHOR2 = "AAA4"

filename = "../logs/positions.csv"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((TCP_IP, TCP_PORT))
sock.listen(1)

print(f"***Server listening on port {TCP_PORT}***")

data, addr = sock.accept()
print(f"***Connection accepted from {addr}***")

distance_a1_a2 = 0.9398
meter2pixel = 400
range_offset = 0.0

with open(filename, "w", newline = "") as file: #clear the file
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


def read_data():

    line = data.recv(1024).decode('UTF-8')

    uwb_list = []

    parts = line.split("}{")    #handles multiple JSON objects at the same time
    last_part = parts[-1]

    if not last_part.startswith("{"):
        last_part = "{" + last_part

    line = last_part

    try:
        uwb_data = json.loads(line)
        uwb_list = uwb_data["links"]
    except Exception as e:
        print("EXCEPTION!", e, line)

    return uwb_list


def tag_pos(a, b, c):
    x=0
    y=0

    if (b != 0 and c != 0) :
        cos_a = (b * b + c * c - a * a) / (2 * b * c)
        x = b * cos_a
        sin_a = (1 - cos_a * cos_a) ** 0.5
        y = b * sin_a

    return round(x.real, 3), round(y.real, 3)


def main():

    screen = turtle.Screen()
    screen.setup(1200, 800)
    screen.tracer(True)

    t_ui = turtle.Turtle()
    t_a1 = turtle.Turtle()
    t_a2 = turtle.Turtle()
    t_a3 = turtle.Turtle()
    turtle_init(t_ui)
    turtle_init(t_a1)
    turtle_init(t_a2)
    turtle_init(t_a3)

    a1_range = 0.0
    a2_range = 0.0

    draw_ui(t_ui)

    while True:
        node_count = 0
        list = read_data()

        for one in list:
            if one["A"] == ANCHOR1:
                clean(t_a1)
                a1_range = float(one["R"])
                draw_uwb_anchor(-350, 150, "ANCHOR1(0,0)", t_a1)
                node_count += 1

            if one["A"] == ANCHOR2:
                clean(t_a2)
                a2_range = float(one["R"])
                draw_uwb_anchor(-350 + meter2pixel * distance_a1_a2,
                                150, "ANCHOR2(" + str(distance_a1_a2)+",0)", t_a2)
                node_count += 1

        if node_count == 2:
            x, y = tag_pos(a2_range, a1_range, distance_a1_a2)

            with open(filename, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([x, y])

            clean(t_a3)
            draw_uwb_tag(x, y, "TAG", t_a3)

        time.sleep(0.1)

    turtle.mainloop()


if __name__ == '__main__':
    main()