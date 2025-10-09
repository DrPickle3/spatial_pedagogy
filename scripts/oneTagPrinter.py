import time
import matplotlib.pyplot as plt
import numpy as np
import utils

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

positions = []

true_dist = 2.6416
min_x = 2
max_x = 3


def tag_pos(ranges, anchors):
    keys = [k for k in ranges if k in anchors]
    dists = np.array([ranges[k] for k in keys])

    return dists[0]


def update_scatter_1d(real_distance=true_dist):
    if not positions:
        return
    plt.clf()

    xs = np.array(positions)

    # --- Histogram + mode computation ---
    counts, bin_edges = np.histogram(xs, bins=30, range=(0, 3))
    mode_index = np.argmax(counts)
    mode_center = (bin_edges[mode_index] + bin_edges[mode_index + 1]) / 2

    # --- Plot histogram ---
    plt.hist(xs, bins=30, range=(0, 3), color="lightgray", edgecolor="black",
             alpha=0.6, label="Distribution des mesures")

    # --- Plot jittered points ---
    jitter_y = np.random.normal(0, 0.02, len(xs))
    plt.scatter(xs, jitter_y, c="blue", s=20, alpha=0.6, label="Mesures individuelles")

    # --- Add mode (most common measured region) ---
    plt.axvline(mode_center, color="red", linestyle="--", linewidth=2, label=f"Mode ≈ {mode_center:.2f} m")

    # --- Add real distance reference, if provided ---
    if real_distance is not None:
        plt.axvline(real_distance, color="green", linestyle="-", linewidth=2, label=f"Distance réelle = {real_distance:.2f} m")

    # --- Formatting ---
    plt.xlabel("Distance mesurée (m)")
    plt.ylabel("Fréquence / Densité")
    plt.title("Histogramme + Jitter - Précision de mesure")
    plt.xlim(min_x, max_x)
    plt.legend()
    plt.grid(True, axis="x")
    plt.pause(0.01)
    return plt


def on_exit():
    update_scatter_1d(true_dist).savefig("../images/1d.png")
    plt.close('all')


def main():
    sock = utils.connect_wifi()
    utils.clear_file()

    try:
        while True:
            print(f"***Waiting for connection on port {TCP_PORT}***")
            conn, addr = sock.accept()
            print(f"***Connection accepted from {addr}***")

            try:
                buffer = ""
                while True:
                    list, buffer = utils.read_data(conn, buffer)  # pass `conn` instead of global `data`
                    ranges = {}

                    for one in list:
                        if one["A"] in anchors:
                            ranges[one["A"]] = float(one["R"])

                    if len(ranges) >= 1:
                        x = tag_pos(ranges, anchors)
                        
                        if x > 0.01:
                            positions.append(x)
                        update_scatter_1d()

                    time.sleep(0.1)

            except (ConnectionResetError, BrokenPipeError):
                print(f"***Connection lost from {addr}, waiting for new device...***")
                continue
    except KeyboardInterrupt:
        on_exit()


if __name__ == '__main__':
    main()
