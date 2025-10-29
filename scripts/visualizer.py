import argparse
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.widgets import Slider, Button
import utils


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


def smart_anchors(csv_filename, anchors):
    used_anchors = set()
    with open(csv_filename, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                for i in range(1, 5):
                    anchor_id = row.get(f"id_{i}")
                    if anchor_id:
                        used_anchors.add(anchor_id)
            except ValueError:
                continue  # skip invalid rows
    return {k: v for k, v in anchors.items() if k in used_anchors}


def update_scatter_from_csv(csv_filename, anchors, trail_length):
    # --- Load CSV data ---
    xs, ys, timestamps = [], [], []
    with open(csv_filename, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                # Last columns are x, y, timestamp
                x = float(row.get("pos_x"))
                y = float(row.get("pos_y"))
                t = row.get("Timestamp")
                xs.append(x)
                ys.append(y)
                timestamps.append(t)
            except ValueError:
                continue  # skip invalid rows

    xs, ys = np.array(xs), np.array(ys)

    mean_x, mean_y = np.mean(xs), np.mean(ys)
    std_x, std_y = np.std(xs), np.std(ys)
    var_x, var_y = np.var(xs), np.var(ys)
    gaussian_circle = Ellipse(
        (mean_x, mean_y),
        width=4*std_x,  #4*std pour avoir environ 95.4% dans l'ellipse
        height=4*std_y,
        edgecolor='orange',
        facecolor='none',
        linestyle='--',
        linewidth=1.5,
        label=f"Incertitude (2σ) — VarX={var_x:.3f}, VarY={var_y:.3f}"
    )
    
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

    #Gaussian
    ax.add_patch(gaussian_circle)

    #Real point + Mean Comparison
    ax.plot([2.3622], [1.905], 'go', markersize=6, label="Position réelle")
    ax.plot([mean_x], [mean_y], 'yo', markersize=6, label="Position moyenne")

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

    #grid lines
    ax.set_xticks(np.arange(x_min, x_max + 1, 1))  # major ticks every 1 m
    ax.set_yticks(np.arange(y_min, y_max + 1, 1))
    ax.set_xticks(np.arange(x_min, x_max + 0.2, 0.2), minor=True)
    ax.set_yticks(np.arange(y_min, y_max + 0.2, 0.2), minor=True)

    # Draw grids
    ax.grid(which='major', linestyle=':', color='gray', linewidth=1, alpha=0.7)
    ax.grid(which='minor', linestyle=':', color='gray', linewidth=0.5, alpha=0.3)

    #title
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

    anchors = utils.load_anchors()
    anchors = smart_anchors(args.filename, anchors)

    try:
        update_scatter_from_csv(args.filename, anchors, args.trail)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
