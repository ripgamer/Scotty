from dataclasses import dataclass
from time import time
from typing import Any, Callable, Dict, Protocol, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from scotty.fun_evolution import ray_evolution_2D_fun
from scotty.fun_general import K_magnitude, find_normalised_gyro_freq
from scotty.geometry import MagneticField
from scotty.hamiltonian import Hamiltonian
from scotty.typing import FloatArray


class _Event(Protocol):
    """Protocol describing a `scipy.integrate.solve_ivp` event callback"""

    terminal: bool = False
    direction: float = 0.0

    def __call__(self, *args):
        pass


def _event(terminal: bool, direction: float):
    """Decorator to add the attributes required for `scipy.integrate.solve_ivp` while
    keepying mypy happy

    """

    def decorator_event(func: Any) -> _Event:
        # Stop the solver when the beam leaves the plasma
        func.terminal = terminal
        # positive value, when function result goes from negative to positive
        func.direction = direction
        return func

    return decorator_event


def make_solver_events(
    poloidal_flux_enter: float, launch_angular_frequency: float, field: MagneticField
) -> Dict[str, Callable]:
    """Define event handlers for the ray solver

    Only works correctly for the 2D case

    Parameters
    ----------
    poloidal_flux_enter : float
        Poloidal flux label of plasma surface
    launch_angular_frequency : float
        Beam frequency
    field : MagneticField
        Magnetic field object

    Returns
    -------
    Dict[str, Callable]
        Dictionary of event handlers with names

    """

    @_event(terminal=True, direction=1.0)
    def event_leave_plasma(
        tau, ray_parameters_2D, K_zeta: float, hamiltonian: Hamiltonian
    ):
        q_R, q_Z, _, _ = ray_parameters_2D
        poloidal_flux = field.poloidal_flux(q_R, q_Z)

        # Leave at the same poloidal flux of entry
        # goes from negative to positive when leaving the plasma
        return poloidal_flux - poloidal_flux_enter

    @_event(terminal=False, direction=1.0)
    def event_leave_LCFS(
        tau, ray_parameters_2D, K_zeta: float, hamiltonian: Hamiltonian
    ):
        q_R, q_Z, _, _ = ray_parameters_2D
        poloidal_flux = field.poloidal_flux(q_R, q_Z)
        poloidal_flux_LCFS = 1.0
        # goes from negative to positive when leaving the LCFS
        return poloidal_flux - poloidal_flux_LCFS

    # Capture bounding box of magnetic field
    data_R_coord_min = field.R_coord.min()
    data_R_coord_max = field.R_coord.max()
    data_Z_coord_min = field.Z_coord.min()
    data_Z_coord_max = field.Z_coord.max()

    @_event(terminal=True, direction=-1.0)
    def event_leave_simulation(
        tau, ray_parameters_2D, K_zeta: float, hamiltonian: Hamiltonian
    ):
        q_R, q_Z, _, _ = ray_parameters_2D

        is_inside = (
            (q_R > data_R_coord_min)
            and (q_R < data_R_coord_max)
            and (q_Z > data_Z_coord_min)
            and (q_Z < data_Z_coord_max)
        )

        # goes from positive (True) to negative(False) when leaving the simulation region
        return is_inside

    @_event(terminal=True, direction=0.0)
    def event_cross_resonance(tau, ray_parameters_2D, K_zeta, hamiltonian: Hamiltonian):
        # Currently only works when crossing resonance.
        # To implement crossing of higher harmonics as well
        delta_gyro_freq = 0.01

        q_R, q_Z, _, _ = ray_parameters_2D

        B_R = field.B_R(q_R, q_Z)
        B_T = field.B_T(q_R, q_Z)
        B_Z = field.B_Z(q_R, q_Z)

        B_Total = np.sqrt(B_R**2 + B_T**2 + B_Z**2)
        gyro_freq = find_normalised_gyro_freq(B_Total, launch_angular_frequency)

        # The function's return value gives zero when the gyrofreq on the ray goes from either
        # above to below or below to above the resonance.
        return (gyro_freq - 1.0 - delta_gyro_freq) * (gyro_freq - 1.0 + delta_gyro_freq)

    @_event(terminal=False, direction=1.0)
    def event_reach_K_min(tau, ray_parameters_2D, K_zeta, hamiltonian: Hamiltonian):
        # To find tau of the cut-off, that is the location where the
        # wavenumber K is minimised
        # This function finds the turning points

        q_R = ray_parameters_2D[0]
        q_Z = ray_parameters_2D[1]
        K_R = ray_parameters_2D[2]
        K_Z = ray_parameters_2D[3]
        K_magnitude = np.sqrt(K_R**2 + K_Z**2 + K_zeta**2 / q_R**2)

        dH = hamiltonian.derivatives(q_R, q_Z, K_R, K_zeta, K_Z)

        d_K_d_tau = -(1 / K_magnitude) * (
            dH["dH_dR"] * K_R + dH["dH_dZ"] * K_Z + dH["dH_dKR"] * q_R
        )
        return d_K_d_tau

    return {
        "leave_plasma": event_leave_plasma,
        "leave_LCFS": event_leave_LCFS,
        "leave_simulation": event_leave_simulation,
        "cross_resonance": event_cross_resonance,
        "reach_K_min": event_reach_K_min,
    }


def handle_leaving_plasma_events(
    tau_events: Dict[str, FloatArray], ray_parameters_2D_events: FloatArray
) -> float:
    """Handle events detected by `scipy.integrate.solve_ivp`. This
    only handles events due to the ray leaving the plasma or
    simulation:

    - ``"leave_plasma"``: the ray has left the plasma
    - ``"leave_LCFS"``: the ray has left the last-closed flux
      surface. For most simulations, this is likely identical to
      leaving the plasma
    - ``"leave_simulation"``: the ray has left the simulated area
      (essentially the bounding box of the plasma)
    - ``"cross_resonance"``: the ray has crossed a resonance

    Parameters
    ----------
    tau_events : Dict[str, FloatArray]
        A mapping between event names and the solver ``t_events``
    K_R_LCFS : float
        The radial wavevector in the case where the beam has crossed
        the LCFS

    Returns
    -------
    FloatArray
        The value of ``tau`` when the detected event first occurred

    """

    def detected(event):
        """True if ``event`` was detected"""
        return len(tau_events[event]) != 0

    # Event names here must match those in the `solver_ray_events`
    # dict defined outside this function
    if detected("leave_plasma") and not detected("leave_LCFS"):
        return tau_events["leave_plasma"][0]

    if detected("cross_resonance"):
        return tau_events["cross_resonance"][0]

    if not detected("leave_plasma") and detected("leave_LCFS"):
        return tau_events["leave_LCFS"][0]

    if detected("leave_plasma") and detected("leave_LCFS"):
        # If both event_leave_plasma and event_leave_LCFS occur
        K_R_LCFS = ray_parameters_2D_events[0][2]
        if K_R_LCFS < 0:
            # Beam has gone through the plasma, terminate at LCFS
            return tau_events["leave_LCFS"][0]

        # Beam deflection sufficiently large, terminate at entry poloidal flux
        return tau_events["leave_plasma"][0]

    # If one ends up here, things aren't going well. I can think of
    # two possible reasons:
    # - The launch conditions are really weird (hasn't happened yet,
    #   in my experience)
    # - The max_step setting of the solver is too large, such that the
    #   ray leaves the LCFS and enters a region where `poloidal_flux <
    #   1` in a single step. The solver thus doesn't log the event
    #   when it really should

    print("Warning: Ray has left the simulation region without leaving the LCFS.")
    return tau_events["leave_simulation"][0]


def handle_no_resonance(
    solver_ray_output,
    tau_leave: float,
    tau_points: FloatArray,
    K_zeta: float,
    solver_arguments,
    event_leave_plasma: Callable,
) -> FloatArray:
    """Add an additional tau point at the cut-off (minimum K) if the
    beam does NOT reach a resonance

    Propagates another ray to find the cut-off location

    TODO
    ----
    Check if using ``dense_output`` in the initial ray solver can get
    the same information better/faster

    """
    ray_parameters_2D = solver_ray_output.y
    tau_ray = solver_ray_output.t

    max_tau_idx = int(np.argmax(tau_ray[tau_ray <= tau_leave]))

    K_magnitude_ray = K_magnitude(
        K_R=ray_parameters_2D[2, :max_tau_idx],
        K_zeta=K_zeta,
        K_Z=ray_parameters_2D[3, :max_tau_idx],
        q_R=ray_parameters_2D[0, :max_tau_idx],
    )

    index_cutoff_estimate = int(np.argmin(K_magnitude_ray))
    start = max(0, index_cutoff_estimate - 1)
    stop = min(len(tau_ray) - 1, index_cutoff_estimate + 1)

    ray_parameters_2D_initial_fine = ray_parameters_2D[:, start]
    tau_start_fine = tau_ray[start]
    tau_end_fine = tau_ray[stop]
    tau_points_fine = np.linspace(tau_start_fine, tau_end_fine, 1001)

    solver_start_time = time()

    solver_ray_output_fine = solve_ivp(
        ray_evolution_2D_fun,
        [tau_start_fine, tau_end_fine],
        ray_parameters_2D_initial_fine,
        method="RK45",
        t_eval=tau_points_fine,
        dense_output=False,
        events=event_leave_plasma,
        vectorized=False,
        args=solver_arguments,
    )

    solver_end_time = time()
    print("Time taken (cut-off finder)", solver_end_time - solver_start_time, "s")

    K_magnitude_ray_fine = K_magnitude(
        K_R=solver_ray_output_fine.y[2, :],
        K_zeta=K_zeta,
        K_Z=solver_ray_output_fine.y[3, :],
        q_R=solver_ray_output_fine.y[0, :],
    )
    index_cutoff_fine = np.argmin(K_magnitude_ray_fine)
    tau_cutoff_fine = float(solver_ray_output_fine.t[index_cutoff_fine])
    return np.sort(np.append(tau_points, tau_cutoff_fine))


@dataclass
class K_cutoff_data:
    q_R: float
    q_Z: float
    K_norm_min: float
    poloidal_flux: float
    theta_m: float


def quick_K_cutoff(
    ray_parameters_turning_pt: FloatArray, K_zeta: float, field: MagneticField
) -> K_cutoff_data:
    r"""Calculate some quantities at the minimum :math:`|K|` along the ray

    Parameters
    ----------
    ray_parameters_turning_pt : FloatArray
        State vector from ray evolution
    K_zeta : float
        :math:`K_\zeta` for the ray
    field : MagneticField
        Object describing the magnetic field

    Returns
    -------
    q_R, q_Z, K_norm, poloidal_flux, theta_m
        Ray coordinates, :math:`|K|`, magnetic flux, and mismatch
        angle

    """

    K_turning_pt = np.array(
        [
            K_magnitude(K_R, K_zeta, K_Z, q_R)
            for (q_R, _, K_R, K_Z) in ray_parameters_turning_pt
        ]
    )
    K_min_idx = np.argmin(K_turning_pt)
    q_R, q_Z, K_R, K_Z = ray_parameters_turning_pt[K_min_idx]

    B_R = field.B_R(q_R, q_Z)
    B_T = field.B_T(q_R, q_Z)
    B_Z = field.B_Z(q_R, q_Z)
    B = np.array([B_R, B_T, B_Z])

    K = np.array([K_R, K_zeta / q_R, K_Z])
    K_norm_min = K_turning_pt[K_min_idx]

    sin_theta_m = np.dot(B, K) / (K_norm_min * np.linalg.norm(B))
    # Assumes the mismatch angle is never smaller than -90deg or bigger than 90deg
    theta_m = np.sign(sin_theta_m) * np.arcsin(abs(sin_theta_m))

    poloidal_flux = field.poloidal_flux(q_R, q_Z)

    return K_cutoff_data(q_R, q_Z, K_norm_min, poloidal_flux, theta_m)
