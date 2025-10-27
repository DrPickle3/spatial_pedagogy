import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button


def build_arg_parser():
    """Build argument parser."""
    p = argparse.ArgumentParser(
        description="Writing position of Tag with Anchors in CSV"
    )    
    p.add_argument('--trail', type=int, default=5,
                    help='Number of previous points to show (e.g. --trail 10)')
    p.add_argument('--filename', type=str, default="../logs/positions.csv",
                    help='CSV file we want to read from')
    return p


def update_scatter_from_csv(csv_filename, anchors, trail_length):
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

    # Anchors
    ax.scatter(anchor_xs, anchor_ys, c="purple", s=80, marker="X", label="Anchors")

    # Dynamic point (moving tag)
    point, = ax.plot([], [], 'ro', markersize=6, label="Position mesurée")
    trail_scatter = ax.scatter([], [], c='blue', s=30, label="Positions antérieures")

    # Labels, legend, etc.
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.invert_yaxis()
    ax.legend()
    ax.grid(True, linestyle=":")
    ax.set_title(f"Carte de trajectoire — Frame 1/{len(xs)}\n{timestamps[0]}")

    # --- Slider setup ---
    ax_slider = plt.axes([0.25, 0.1, 0.5, 0.03])
    slider = Slider(ax_slider, 'Frame', 0, len(xs)-1, valinit=0, valfmt='%d')

    # Place buttons slightly *below* the slider (no overlap)
    ax_prev = plt.axes([0.15, 0.05, 0.05, 0.03])
    ax_next = plt.axes([0.8, 0.05, 0.05, 0.03])
    btn_prev = Button(ax_prev, "◀")
    btn_next = Button(ax_next, "▶")

    # --- Update function ---
    def update(val):
        i = int(slider.val)

        # Main red point
        point.set_data([xs[i]], [ys[i]])

        # Compute ghost trail points
        start = max(0, i - trail_length)
        trail_x = xs[start:i]
        trail_y = ys[start:i]

        # Generate decreasing alpha values for fading effect
        n = len(trail_x)
        if n > 0:
            alphas = np.linspace(0.1, 0.8, n)  # older points are more transparent
            colors = [(0, 0, 1, a) for a in alphas]
            trail_scatter.set_offsets(np.c_[trail_x, trail_y][::-1])
            trail_scatter.set_facecolors(colors[::-1])
        else:
            trail_scatter.set_offsets(np.empty((0, 2)))

        # Update title
        ax.set_title(f"Carte de trajectoire — Frame {i+1}/{len(xs)}\n{timestamps[i]}")
        fig.canvas.draw_idle()

    slider.on_changed(update)

    # --- Initial frame ---
    update(0)

    def next_frame(event):
        fig.canvas.release_mouse(slider.ax)
        current = int(slider.val)
        if current < len(xs) - 1:
            slider.set_val(current + 1)

    def prev_frame(event):
        fig.canvas.release_mouse(slider.ax)
        current = int(slider.val)
        if current > 0:
            slider.set_val(current - 1)

    btn_next.on_clicked(next_frame)
    btn_prev.on_clicked(prev_frame)

    plt.show()


def main():

    parser = build_arg_parser()
    args = parser.parse_args()

    anchors = {
        "AAA1": (0.0, 0.0, 0.0),
        "AAA2": (0.0, 0.0, 1.0),
        "AAA3": (0.0, 0.0, 0.0),
        "AAA4": (0.0, 0.0, 0.0),
        "AAA5": (0.0, 0.0, 0.0),
        "AAA6": (2.921, 0.0, 1.0),
        "AAA7": (0.0, 0.0, 0.0),
    }

    try:
        update_scatter_from_csv(args.filename, anchors, args.trail)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
