# Copyright 2023 - 2023, Valerian Hall-Chen and the Scotty contributors
# SPDX-License-Identifier: GPL-3.0

from scotty.fun_general import (
    make_array_3x3,
    find_Psi_3D_lab,
    find_Psi_3D_plasma,
    find_inverse_2D,
    find_K_lab_Cartesian,
    find_q_lab_Cartesian,
    find_K_lab,
    find_d_poloidal_flux_dR,
    find_d_poloidal_flux_dZ,
    angular_frequency_to_wavenumber,
)
from scotty.hamiltonian import Hamiltonian
from scotty.typing import FloatArray
from scotty.geometry import MagneticField

from typing import Optional

import numpy as np
from scipy.optimize import direct, root_scalar


def launch_beam(
    toroidal_launch_angle_Torbeam: float,
    poloidal_launch_angle_Torbeam: float,
    launch_beam_width: float,
    launch_beam_curvature: float,
    launch_position: FloatArray,
    launch_angular_frequency: float,
    field: MagneticField,
    hamiltonian: Hamiltonian,
    vacuumLaunch_flag: bool = True,
    vacuum_propagation_flag: bool = True,
    Psi_BC_flag: bool = True,
    poloidal_flux_enter: float = 1.0,
    delta_R: float = -1e-4,
    delta_Z: float = 1e-4,
):
    r"""
    Propagate the beam from its initial position at the antenna to
    *just* inside the plasma.

    Parameters
    ----------
    toroidal_launch_angle_Torbeam: float
        Toroidal angle of antenna in TORBEAM convention
    poloidal_launch_angle_Torbeam: float
        Poloidal angle of antenna in TORBEAM convention
    launch_beam_width: float
        Width of the beam at launch
    launch_beam_curvature: float
        Curvatuve of the beam at launch
    launch_position: FloatArray
        Position of the antenna in cylindrical coordinates
    launch_angular_frequency: float
        Angular frequency of the beam at launch
    field: MagneticField
        Object describing the magnetic field of the plasma
    vacuumLaunch_flag: bool
        If ``True``, launch beam from vacuum, otherwise beam launch
        position is inside the plasma already
    vacuum_propagation_flag: bool
        If ``True``, run solver from the launch position, and don't
        use analytical vacuum propagation
    Psi_BC_flag: bool
        If ``True``, use matching boundary conditions at plasma entry
        position, otherwise do no special treatment at plasma boundary
    poloidal_flux_enter: float
        Normalised poloidal flux label of plasma boundary
    delta_R: float
        Finite difference spacing to use for ``R``
    delta_Z: float
        Finite difference spacing to use for ``Z``

    Returns
    -------
    K_initial: FloatArray
        Wavevector at plasma entry point
    initial_position: FloatArray
        Coordinates of entry point
    launch_K: FloatArray
        Wavevector at launch point
    Psi_3D_lab_initial: FloatArray
    Psi_3D_lab_launch: FloatArray
    Psi_3D_lab_entry: FloatArray
    Psi_3D_lab_entry_cartersian: FloatArray
    distance_from_launch_to_entry: float

    """

    toroidal_launch_angle = np.deg2rad(toroidal_launch_angle_Torbeam)
    poloidal_launch_angle = np.deg2rad(poloidal_launch_angle_Torbeam)

    wavenumber_K0 = angular_frequency_to_wavenumber(launch_angular_frequency)

    K_R_launch = (
        -wavenumber_K0 * np.cos(toroidal_launch_angle) * np.cos(poloidal_launch_angle)
    )
    K_zeta_launch = (
        -wavenumber_K0
        * np.sin(toroidal_launch_angle)
        * np.cos(poloidal_launch_angle)
        * launch_position[0]
    )
    K_Z_launch = -wavenumber_K0 * np.sin(poloidal_launch_angle)
    launch_K = np.array([K_R_launch, K_zeta_launch, K_Z_launch])

    poloidal_rotation_angle = poloidal_launch_angle + (np.pi / 2)

    Psi_w_beam_diagonal = (
        wavenumber_K0 * launch_beam_curvature + 2j * launch_beam_width ** (-2)
    )
    Psi_w_beam_launch_cartersian = np.eye(2) * Psi_w_beam_diagonal

    rotation_matrix_pol = np.array(
        [
            [np.cos(poloidal_rotation_angle), 0, np.sin(poloidal_rotation_angle)],
            [0, 1, 0],
            [-np.sin(poloidal_rotation_angle), 0, np.cos(poloidal_rotation_angle)],
        ]
    )

    rotation_matrix_tor = np.array(
        [
            [np.cos(toroidal_launch_angle), np.sin(toroidal_launch_angle), 0],
            [-np.sin(toroidal_launch_angle), np.cos(toroidal_launch_angle), 0],
            [0, 0, 1],
        ]
    )

    rotation_matrix = np.matmul(rotation_matrix_pol, rotation_matrix_tor)
    rotation_matrix_inverse = np.transpose(rotation_matrix)

    Psi_3D_beam_launch_cartersian = make_array_3x3(Psi_w_beam_launch_cartersian)
    Psi_3D_lab_launch_cartersian = np.matmul(
        rotation_matrix_inverse,
        np.matmul(Psi_3D_beam_launch_cartersian, rotation_matrix),
    )
    Psi_3D_lab_launch = find_Psi_3D_lab(
        Psi_3D_lab_launch_cartersian,
        launch_position[0],
        launch_position[1],
        K_R_launch,
        K_zeta_launch,
    )

    if not vacuum_propagation_flag:
        return (
            [K_R_launch, K_zeta_launch, K_Z_launch],
            launch_position,
            launch_K,
            Psi_3D_lab_launch,
            Psi_3D_lab_launch,
            None,
            np.full_like(Psi_3D_lab_launch, fill_value=np.nan),
            None,
        )

    Psi_w_beam_inverse_launch_cartersian = find_inverse_2D(Psi_w_beam_launch_cartersian)

    entry_position = find_entry_point(
        launch_position,
        poloidal_launch_angle,
        toroidal_launch_angle,
        poloidal_flux_enter,
        field,
    )

    distance_from_launch_to_entry = np.sqrt(
        launch_position[0] ** 2
        + entry_position[0] ** 2
        - 2
        * launch_position[0]
        * entry_position[0]
        * np.cos(entry_position[1] - launch_position[1])
        + (launch_position[2] - entry_position[2]) ** 2
    )

    # Calculate entry parameters from launch parameters
    # That is, find beam at start of plasma given its parameters at the antenna
    K_lab_launch = np.array([K_R_launch, K_zeta_launch, K_Z_launch])
    K_lab_Cartesian_launch = find_K_lab_Cartesian(K_lab_launch, launch_position)
    K_lab_Cartesian_entry = K_lab_Cartesian_launch
    entry_position_Cartesian = find_q_lab_Cartesian(entry_position)
    K_lab_entry = find_K_lab(K_lab_Cartesian_entry, entry_position_Cartesian)

    K_R_entry = K_lab_entry[0]  # K_R
    K_zeta_entry = K_lab_entry[1]
    K_Z_entry = K_lab_entry[2]  # K_z

    Psi_w_beam_inverse_entry_cartersian = (
        distance_from_launch_to_entry / (wavenumber_K0) * np.eye(2)
        + Psi_w_beam_inverse_launch_cartersian
    )
    # 'entry' is still in vacuum, so the components of Psi along g are
    # all 0 (since \nabla H = 0)
    Psi_3D_beam_entry_cartersian = make_array_3x3(
        find_inverse_2D(Psi_w_beam_inverse_entry_cartersian)
    )
    Psi_3D_lab_entry_cartersian = np.matmul(
        rotation_matrix_inverse,
        np.matmul(Psi_3D_beam_entry_cartersian, rotation_matrix),
    )

    # Convert to cylindrical coordinates
    Psi_3D_lab_entry = find_Psi_3D_lab(
        Psi_3D_lab_entry_cartersian,
        entry_position[0],
        entry_position[1],
        K_R_entry,
        K_zeta_entry,
    )

    # -------------------
    # Find initial parameters in plasma
    # -------------------
    K_R_initial = K_R_entry
    K_zeta_initial = K_zeta_entry
    K_Z_initial = K_Z_entry
    initial_position = entry_position
    if Psi_BC_flag:  # Use BCs
        dH = hamiltonian.derivatives(
            initial_position[0],
            initial_position[2],
            K_R_initial,
            K_zeta_initial,
            K_Z_initial,
        )

        dH_dR_initial = dH["dH_dR"]
        dH_dZ_initial = dH["dH_dZ"]
        dH_dKR_initial = dH["dH_dKR"]
        dH_dKzeta_initial = dH["dH_dKzeta"]
        dH_dKZ_initial = dH["dH_dKZ"]
        d_poloidal_flux_d_R_boundary = find_d_poloidal_flux_dR(
            initial_position[0],
            initial_position[2],
            delta_R,
            field.poloidal_flux,
        )
        d_poloidal_flux_d_Z_boundary = find_d_poloidal_flux_dZ(
            initial_position[0],
            initial_position[2],
            delta_R,
            field.poloidal_flux,
        )

        Psi_3D_lab_initial = find_Psi_3D_plasma(
            Psi_3D_lab_entry,
            dH_dKR_initial,
            dH_dKzeta_initial,
            dH_dKZ_initial,
            dH_dR_initial,
            dH_dZ_initial,
            d_poloidal_flux_d_R_boundary,
            d_poloidal_flux_d_Z_boundary,
        )
    else:  # Do not use BCs
        Psi_3D_lab_initial = Psi_3D_lab_entry

    return (
        [K_R_initial, K_zeta_initial, K_Z_initial],
        initial_position,
        launch_K,
        Psi_3D_lab_initial,
        Psi_3D_lab_launch,
        Psi_3D_lab_entry,
        Psi_3D_lab_entry_cartersian,
        distance_from_launch_to_entry,
    )


def find_entry_point(
    launch_position: FloatArray,
    poloidal_launch_angle: float,
    toroidal_launch_angle: float,
    poloidal_flux_enter: float,
    field: MagneticField,
    boundary_adjust: float = 1e-8,
) -> FloatArray:
    """Find the coordinates where the beam enters the plasma.

    Arguments
    ---------
    launch_position:
        Cartesian coordinates of the antenna (or cylindrical with
        zeta=0)
    poloidal_launch_angle:
        Poloidal angle of the antenna (radians), clockwise from the
        horizontal axis
    toroidal_launch_angle:
        Toroidal angle of the antenna (radians), anti-clockwise from
        the negative X-axis
    field:
        Object describing the magnetic field geometry
    boundary_adjust:
        Step size used to ensure entry point is _just_ inside plasma

    Returns
    -------
    Array with cylindrical coordinates of entry point
    """

    # We know that the plasma is contained entirely within ``field``'s
    # (R, Z) grid, so the maximum distance the beam could possibly
    # travel before hitting the plasma is when it's aimed at the
    # top/bottom corner of the grid on the far side of the torus. This
    # an overestimate, but it's only used to parameterize the beam
    X_start, Y_start, Z_start = launch_position
    X_length = abs(X_start) + field.R_coord.max()
    Z_length = abs(Z_start) + field.Z_coord.max()
    max_length = np.hypot(X_length, Z_length)

    # TORBEAM antenna angles are anti-clockwise from negative X-axis,
    # so we need to rotate the toroidal angle by pi. This will take
    # care of the direction of the beam. The poloidal angle is also
    # reversed from its usual sense, so we can just flip it
    toroidal_launch_angle = toroidal_launch_angle + np.pi
    poloidal_launch_angle = -poloidal_launch_angle

    # We parameterise beam in a line normal to the antenna up to
    # max_length, and we can be sure the beam will either hit the
    # plasma or miss it entirely.
    X_step = max_length * np.cos(toroidal_launch_angle) * np.cos(poloidal_launch_angle)
    Y_step = max_length * np.sin(toroidal_launch_angle) * np.cos(poloidal_launch_angle)
    Z_step = max_length * np.sin(poloidal_launch_angle)
    step_array = np.array((X_step, Y_step, Z_step))

    def beam_line(tau):
        """Parameterised line in beam direction"""
        return launch_position + tau * step_array

    def cartesian_to_cylindrical(X, Y, Z):
        """Cartesian to cylindrical coordinates"""
        return np.sqrt(X**2 + Y**2), np.arctan2(Y, X), Z

    def poloidal_flux_boundary_along_line(tau):
        """Signed poloidal flux distance to plasma boundary"""
        R, _, Z = cartesian_to_cylindrical(*beam_line(tau))
        return field.poloidal_flux(R, Z) - poloidal_flux_enter

    # Find the plasma boundary using a bracket search. We need the
    # minimum so that the flux has different sign to our initial
    # position for the bracket points. There could be one or two
    # minima (corresponding to the two halves of the torus), we only
    # care about the closest, so use the first result as a bound for
    # the second. If there isn't a second, this will just find the
    # first again
    first_min = direct(
        poloidal_flux_boundary_along_line, bounds=((0, 1),), len_tol=1e-3
    )
    minimum = direct(
        poloidal_flux_boundary_along_line, bounds=((0, first_min.x),), len_tol=1e-3
    )
    # If the closest minimum is positive, then the beam never actually
    # enters the plasma, and we should abort
    if minimum.fun > 0:
        R_miss, zeta_miss, Z_miss = cartesian_to_cylindrical(*beam_line(minimum.x))
        miss_coords = f"(R={R_miss}, zeta={zeta_miss}, Z={Z_miss})"
        raise RuntimeError(
            f"Beam does not hit plasma. Closest point is at {miss_coords}, "
            f"distance in poloidal flux to boundary={minimum.fun}"
        )

    # `minimum.x` is some point along the beam that's definitely
    # inside the plasma. So any root between the start of the beam and
    # this point is the closest entry point
    boundary = root_scalar(poloidal_flux_boundary_along_line, bracket=(0, minimum.x))
    if not boundary.converged:
        raise RuntimeError(
            f"Could not find plasma boundary, root finding failed with '{boundary.flag}'"
        )

    # The root might be just outside the plasma due to floating point
    # errors, if so, take small steps until we're definitely inside
    boundary_tau = boundary.root
    R_boundary, _, Z_boundary = cartesian_to_cylindrical(*beam_line(boundary_tau))
    if field.poloidal_flux(R_boundary, Z_boundary) > poloidal_flux_enter:
        boundary_tau += boundary_adjust

    return np.array(cartesian_to_cylindrical(*beam_line(boundary.root)))
