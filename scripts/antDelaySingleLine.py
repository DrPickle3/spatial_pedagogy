import numpy as np
from scipy.optimize import minimize

def main():

    # Known values
    c = 299_702_547           # m/s
    tick_duration = 15.65e-12 # s
    meters_per_tick = c * tick_duration

    # Distances
    true_distance = 2.4892    # real distance between tag and anchor
    measured_distance = 2.46 # measured distance

    # Tag delay is already calibrated, so assume tau_tag = 0
    tau_tag = 0

    # Compute anchor delay in meters
    tau_anchor = measured_distance - true_distance - tau_tag

    # Convert to ticks
    tau_anchor_ticks = tau_anchor / meters_per_tick

    print(f"Anchor antenna delay: {tau_anchor:.4f} meters, {tau_anchor_ticks:.0f} ticks")




if __name__ == "__main__":
    main()
