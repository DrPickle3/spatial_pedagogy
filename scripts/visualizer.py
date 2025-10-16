import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

def update_scatter_from_csv(csv_filename, anchors, bin_size=0.3):
    # --- Load CSV data ---
    xs, ys, timestamps = [], [], []
    with open(csv_filename, newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            try:
                # Last columns are x, y, timestamp
                x = float(row[-3])
                y = float(row[-2])
                t = row[-1]
                xs.append(x)
                ys.append(y)
                timestamps.append(t)
            except ValueError:
                continue  # skip invalid rows

    xs, ys = np.array(xs), np.array(ys)
    anchor_xs = [coord[0] for coord in anchors.values()]
    anchor_ys = [coord[1] for coord in anchors.values()]

    # --- Determine plot limits ---
    all_x = np.concatenate([xs, anchor_xs])
    all_y = np.concatenate([ys, anchor_ys])
    padding = 1
    x_min, x_max = all_x.min() - padding, all_x.max() + padding
    y_min, y_max = all_y.min() - padding, all_y.max() + padding

    # --- Create figure and initial plot ---
    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.25)

    # Density map (2D histogram)
    counts, xedges, yedges, im = ax.hist2d(
        xs, ys,
        bins=[
            int(np.ceil((x_max - x_min) / bin_size)),
            int(np.ceil((y_max - y_min) / bin_size))
        ],
        range=[[x_min, x_max], [y_min, y_max]],
        cmap='Blues',
        alpha=0.7
    )

    # Anchors
    ax.scatter(anchor_xs, anchor_ys, c="purple", s=80, marker="X", label="Anchors")

    # Dynamic point (moving tag)
    point, = ax.plot([], [], 'ro', markersize=6, label="Position mesurée")

    # Labels, legend, etc.
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.invert_yaxis()
    ax.legend()
    ax.grid(True, linestyle=":")
    ax.set_title(f"Carte de trajectoire — Frame 1/{len(xs)}\n{timestamps[0]}")

    plt.colorbar(im, ax=ax, label="Nombre de mesures")

    # --- Slider setup ---
    ax_slider = plt.axes([0.15, 0.1, 0.7, 0.03])
    slider = Slider(ax_slider, 'Frame', 0, len(xs)-1, valinit=0, valfmt='%d')

    # --- Update function ---
    def update(frame_idx):
        i = int(slider.val)
        point.set_data([xs[i]], [ys[i]])  # must be lists
        ax.set_title(f"Carte de trajectoire — Frame {i+1}/{len(xs)}\n{timestamps[i]}")
        fig.canvas.draw_idle()

    slider.on_changed(update)

    # --- Initial point ---
    point.set_data([xs[0]], [ys[0]])

    plt.show()

anchors = {
    "AAA1": (0.0, 0.0, 0.0),
    "AAA2": (0.0, 0.0, 0.0),
    "AAA3": (0.0, 0.0, 0.0),
    "AAA4": (0.0, 0.0, 0.0),
    "AAA5": (0.0, 0.0, 0.0),
    "AAA6": (1.0, 0.23, 0.0),
    "AAA7": (0.0, 0.0, 0.0),
}

update_scatter_from_csv("../logs/positions.csv", anchors)
