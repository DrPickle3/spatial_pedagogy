import numpy as np
from scipy.optimize import minimize

def main():

    # Speed of light and tick duration
    c = 299_702_547  # m/s
    tick_duration = 15.65e-12  # 15.65 ps
    meters_per_tick = c * tick_duration  # ~0.00469 m/tick

    # Devices
    devices = ['Tag', 'Anchor1', 'Anchor4']

    # True distances between devices (in meters)
    true_distances = {
        ('Tag', 'Anchor1'): 2.8702,
        ('Tag', 'Anchor4'): 2.5908,
        ('Anchor1', 'Anchor4'): 1.7018
    }

    # Measured distances (in meters)
    measured_distances = {
        ('Tag', 'Anchor1'): 3.449,
        ('Tag', 'Anchor4'): 3.045,
        ('Anchor1', 'Anchor4'): 2.370
    }

    # Objective function: sum of squared differences between corrected and true distances
    def objective(tau_m):
        error = 0.0
        for (d1, d2), true_d in true_distances.items():
            measured_d = measured_distances[(d1, d2)]
            idx1 = devices.index(d1)
            idx2 = devices.index(d2)
            corrected_d = measured_d - tau_m[idx1] - tau_m[idx2]
            error += (corrected_d - true_d)**2
        return error

    # Initial guess (all zeros)
    initial_guess = np.zeros(len(devices))

    # Minimize
    res = minimize(objective, initial_guess)

    # Optimized delays
    tau_m_opt = res.x
    tau_ticks_opt = tau_m_opt / meters_per_tick

    # Print results
    print("Antenna delay corrections:")
    for i, device in enumerate(devices):
        print(f"{device}: {tau_m_opt[i]:.4f} meters, {tau_ticks_opt[i]:.0f} ticks")

    # Optional: print residual error
    print(f"\nResidual error: {res.fun:.6f} m^2")



if __name__ == "__main__":
    main()
