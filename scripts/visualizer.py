import argparse
import csv
from datetime import datetime
import json
import os
import subprocess

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.widgets import RangeSlider, Button

import numpy as np
from scipy.ndimage import uniform_filter1d

import utils


def build_arg_parser():
    """ Builds and returns the argument parser for CLI options. """
    p = argparse.ArgumentParser(
        description="Writing position of Tag with Anchors in CSV"
    )
    p.add_argument('--stops', action='store_true',
                   help='Prints the detected stops')
    p.add_argument('--precision', action='store_true',
                   help='Displays the precision of the entire log')
    p.add_argument('--trail', type=int, default=5,
                    help='Number of previous points to show (e.g. --trail 10)')
    p.add_argument('--csv', type=str, default="../logs/positions.csv",
                    help='CSV file we want to read from')
    p.add_argument('--calibration', action='store_true',
                   help='Calibrate a certain CSV and PNG for visualization.' \
                        'You need to save the results to visualize it !!!' \
                        'You also need to match the anchors with the correct' \
                        'image so the the coordinates fit.')
    return p


def get_positions(csv_filename, stop=False):
    """ Reads x, y, and timestamp data from the CSV file. """
    xs, ys, timestamps, float_timestamps = [], [], [], []
    with open(csv_filename, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                x = float(row.get("x_transformed", row.get("pos_x")))
                y = float(row.get("y_transformed", row.get("pos_y")))

                # For calculations with time
                t = datetime.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S.%f")
                float_timestamps.append(t.timestamp())
                # For display
                t = row.get("Timestamp")
                timestamps.append(t)

                xs.append(x)
                ys.append(y)
            except ValueError:
                continue  # skip invalid rows

    xs, ys = np.array(xs), np.array(ys)

    xs, ys, timestamps, float_timestamps = densify_positions(xs, ys, timestamps, float_timestamps)

    return xs, ys, timestamps, float_timestamps


def densify_positions(xs, ys, timestamps, float_timestamps, max_dt=0.2):
    """
    Inserts interpolated positions if the time difference between samples 
    exceeds max_dt seconds.
    """
    new_xs = [xs[0]]
    new_ys = [ys[0]]
    new_ts = [float_timestamps[0]]
    padded_ts = [timestamps[0]]

    for i in range(1, len(xs)):
        x0, y0, t0 = xs[i-1], ys[i-1], float_timestamps[i-1]
        x1, y1, t1 = xs[i], ys[i], float_timestamps[i]

        ts1 = timestamps[i]

        dt = t1 - t0

        # number of interpolated steps
        if dt > max_dt:
            steps = int(dt // max_dt)

            for s in range(1, steps + 1):
                r = s / (steps + 1)
                new_xs.append(x0 + r * (x1 - x0))
                new_ys.append(y0 + r * (y1 - y0))
                new_ts.append(t0 + r * dt)
                padded_ts.append(padded_ts[-1])

        # always append real measurement
        new_xs.append(x1)
        new_ys.append(y1)
        new_ts.append(t1)
        padded_ts.append(ts1)

    return np.array(new_xs), np.array(new_ys), padded_ts, new_ts


def smart_anchors(anchors, csv_filename):
    """ Returns only the anchors that were used in the CSV file. """
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


def update_scatter_from_csv(anchors, args):
    """ Displays a dynamic trajectory plot of the tag positions. """

        # --- Create figure and initial plot ---
    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.25)

    # Image
    if args.calibration:
        result = subprocess.run(
            ["python", "../calibration/main.py", "--csv", args.csv],
            capture_output=True, text=True
        )

        full_json = {}
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            full_json.update(obj)

        experiment_path = full_json["experiment_path"]

        img_path = os.path.join(experiment_path, "processed_image.png")

        img = mpimg.imread(img_path)

        # Only works if clicked on save (for now)
        args.csv = os.path.join(experiment_path, "calibrated_points.csv")

        new_anchors = os.path.join(experiment_path, "anchors_calibrated.json")
        if os.path.exists(new_anchors):
            anchors = smart_anchors(utils.load_anchors(new_anchors), args.csv)

    # --- Load CSV data ---
    xs, ys, timestamps, float_timestamps = get_positions(args.csv)

    if args.precision:
        mean_x, mean_y = np.mean(xs), np.mean(ys)
        std_x, std_y = np.std(xs), np.std(ys)
        var_x, var_y = np.var(xs), np.var(ys)
        gaussian_circle = Ellipse(
            (mean_x, mean_y),
            width=4*std_x,  # 4*std gives ~95.4% coverage
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
    padding = all_x.max() / 4
    x_min, x_max = all_x.min() - padding, all_x.max() + padding
    y_min, y_max = all_y.min() - padding, all_y.max() + padding

    if args.calibration:
        ax.imshow(img, extent=[x_min, x_max, y_min, y_max], aspect='auto', origin='lower')

    # Anchors
    ax.scatter(anchor_xs, anchor_ys, c="purple", s=80, marker="X", label="Anchors")

    # Stops
    if args.stops:
        useless_xs, useless_ys, useless_ts, stops_pos = detect_stops(args.csv)

        stop_xs = [stop["x"] for stop in stops_pos]
        stop_ys = [stop["y"] for stop in stops_pos]

        ax.scatter(stop_xs, stop_ys, c="red", s=60, marker="s", label="Stops")

    # Gaussian
    if args.precision:
        ax.add_patch(gaussian_circle)

        # Real point + Mean Comparison
        ax.plot([2.3622], [1.905], 'go', markersize=6, label="Position réelle")
        ax.plot([mean_x], [mean_y], 'yo', markersize=6, label="Position moyenne")

    # Dynamic point (moving tag)
    point, = ax.plot([], [], 'go', markersize=6, label="Position mesurée")
    trail_scatter = ax.scatter([], [], c='blue', s=30, label="Positions antérieures")

    # Labels, legend, etc.
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.invert_yaxis()
    ax.legend()

    # Grid lines
    ax.set_xticks(np.arange(x_min, x_max + 1, 50))  # major ticks every 1 m
    ax.set_yticks(np.arange(y_min, y_max + 1, 50))
    ax.set_xticks(np.arange(x_min, x_max + 0.2, 10), minor=True)
    ax.set_yticks(np.arange(y_min, y_max + 0.2, 10), minor=True)

    # Draw grids
    ax.grid(which='major', linestyle=':', color='gray', linewidth=1.5, alpha=0.5)
    ax.grid(which='minor', linestyle=':', color='gray', linewidth=1, alpha=0.3)

    # Title
    ax.set_title(f"Carte de trajectoire — Frame 1/{len(xs)}\n{timestamps[0]}")

    # --- Slider setup ---
    ax_slider = plt.axes([0.25, 0.1, 0.5, 0.03])
    slider = RangeSlider(ax_slider, 'Frame', 1, len(xs), valinit=(1, len(xs)), valfmt='%d')

    # Buttons for navigation
    ax_prev = plt.axes([0.1, 0.1, 0.05, 0.03])
    ax_next = plt.axes([0.9, 0.1, 0.05, 0.03])
    btn_prev = Button(ax_prev, "◀")
    btn_next = Button(ax_next, "▶")

    # --- Update function ---
    def update(val):
        """ Updates plot when slider range changes. """
        start_frame, end_frame = map(int, slider.val)
        selected_x = xs[start_frame-1:end_frame]
        selected_y = ys[start_frame-1:end_frame]
        trail_scatter.set_offsets(np.c_[selected_x, selected_y])
        
        # Keep the red point at the end
        point.set_data([xs[end_frame-1]], [ys[end_frame-1]])

        # Compute ghost trail points
        start = max(0, end_frame - 1 - args.trail)
        trail_x = xs[start:end_frame - 1]
        trail_y = ys[start:end_frame - 1]

        # Fade effect
        n = len(trail_x)
        if n > 0:
            alphas = np.linspace(0.1, 0.8, n)
            colors = [(0, 0, 1, a) for a in alphas]
            trail_scatter.set_offsets(np.c_[trail_x, trail_y][::-1])
            trail_scatter.set_facecolors(colors[::-1])
        else:
            trail_scatter.set_offsets(np.empty((0, 2)))

        ax.set_title(f"Carte de trajectoire — Frame {end_frame}/{len(xs)}\n{timestamps[end_frame - 1]}")
        fig.canvas.draw_idle()

    slider.on_changed(update)

    # --- Initial frame ---
    update(0)

    def next_frame(event):
        fig.canvas.release_mouse(slider.ax)
        start_frame, end_frame = map(int, slider.val)
        if end_frame < len(xs):
            slider.set_val([start_frame, end_frame + 1])

    def prev_frame(event):
        fig.canvas.release_mouse(slider.ax)
        start_frame, end_frame = map(int, slider.val)
        if end_frame > start_frame:
            slider.set_val([start_frame, end_frame - 1])
        elif end_frame > 1:
            slider.set_val([start_frame - 1, end_frame - 1])

    btn_next.on_clicked(next_frame)
    btn_prev.on_clicked(prev_frame)

    plt.show()


def detect_stops(csv_filename, speed_thresh=0.2, min_duration=1.0):
    """ Detects stops based on movement speed threshold and duration. """
    xs, ys, timestamps, float_timestamps = get_positions(csv_filename, True)

    dt = np.diff(float_timestamps)
    dt[dt == 0] = 1e-6
    vx = np.diff(xs) / dt
    vy = np.diff(ys) / dt
    speed = np.sqrt(vx**2 + vy**2)
    speed = np.append(speed, speed[-1])  # align length with positions

    speed_smooth = uniform_filter1d(speed, size=5)
    low = speed_smooth < speed_thresh

    stops = []
    n = len(low)
    i = 0
    while i < n:
        if not low[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and low[j + 1]:
            j += 1

        duration = float_timestamps[j] - float_timestamps[i]
        if duration >= min_duration:
            stops.append({
                "start_frame": i + 1,
                "end_frame": j + 1,
                "x": float(np.mean(xs[i:j+1])),
                "y": float(np.mean(ys[i:j+1])),
            })
        i = j + 1

    return xs, ys, float_timestamps, stops


def show_summary_window(csv_filename):
    """ Displays a static summary window with mean and stop stats. """

    xs, ys, float_timestamps, stops = detect_stops(csv_filename)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis('off')
    ax.set_title("Résumé des mesures", fontsize=14, pad=20, weight='bold')

    # Compute stop durations (if provided)
    durations = []
    if stops:
        for s in stops:
            start, end = s["start_frame"], s["end_frame"]
            durations.append(float_timestamps[end-1] - float_timestamps[start-1])

    if durations:
        mean_stop = np.mean(durations)
        total_stops = len(durations)
    else:
        mean_stop = 0
        total_stops = 0

    # Compute total trajectory length
    dist = np.sum(np.sqrt(np.diff(xs)**2 + np.diff(ys)**2))

    text = (
        f"**Statistiques**\n"
        f"- Nombre total de points : {len(xs)}\n"
        f"- Distance totale parcourue : {dist:.2f} m\n"
        f"- Nombre d'arrêts : {total_stops}\n"
        f"- Durée moyenne d'arrêt : {mean_stop:.2f} s"
    )

    ax.text(0.05, 0.95, text, va='top', ha='left', fontsize=11, family='monospace')
    plt.tight_layout()
    plt.show(block=False)


def main():
    """ Main entry point — parses args and launches visualization or stop detection. """
    parser = build_arg_parser()
    args = parser.parse_args()

    anchors = utils.load_anchors()
    anchors = smart_anchors(anchors, args.csv)

    # if (args.stops):
        # show_summary_window(args.csv)

    try:
        update_scatter_from_csv(anchors, args)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
