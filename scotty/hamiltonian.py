# Copyright 2023 - 2023, Valerian Hall-Chen and the Scotty contributors
# SPDX-License-Identifier: GPL-3.0

from scotty.geometry import MagneticField
from scotty.density_fit import DensityFitLike
from scotty.fun_general import (
    angular_frequency_to_wavenumber,
    find_normalised_gyro_freq,
    find_normalised_plasma_freq,
    contract_special,
)
from scotty.typing import ArrayLike, FloatArray


from dataclasses import dataclass, asdict
import numpy as np
from typing import Dict, Tuple


class DielectricTensor:
    r"""Calculates the components of the cold plasma dielectric tensor for a
    wave with angular frequency :math:`\Omega`:

    .. math::

        \epsilon =
          \begin{pmatrix}
            \epsilon_{11}  & -i\epsilon_{12} & 0 \\
            i\epsilon_{12} & \epsilon_{11}   & 0 \\
            0            & 0             & \epsilon_{bb} \\
          \end{pmatrix}

    where:

    .. math::

        \begin{align}
          \epsilon_{11} &= 1 - \frac{\Omega_{pe}^2}{\Omega^2 - \Omega_{ce}^2} \\
          \epsilon_{12} &=
            1 - \frac{\Omega_{pe}^2\Omega_{ce}}{\Omega(\Omega^2 - \Omega_{ce}^2)} \\
          \epsilon_{bb} &= 1 - \frac{\Omega_{pe}^2}{\Omega^2} \\
        \end{align}

    The components of the dielectric tensor are calculated in the
    :math:`(\hat{\mathbf{u}}_1, \hat{\mathbf{u}}_2, \hat{\mathbf{b}})` basis.
    Hence, :math:`\epsilon_{11}`, :math:`\epsilon_{12}`, and
    :math:`\epsilon_{bb}` correspond to the ``S``, ``D``, and ``P`` variables in
    Stix, respectively. The notation used in this code is chosen to be
    consistent with Hall-Chen, Parra, Hillesheim, PPCF 2022.

    Parameters
    ----------
    electron_density:
        Electron number density
    angular_frequency:
        Angular frequency of the beam
    B_total:
        Magnitude of the magnetic field

    """

    def __init__(
        self,
        electron_density: ArrayLike,
        angular_frequency: float,
        B_total: ArrayLike,
    ):
        _plasma_freq_2 = (
            find_normalised_plasma_freq(electron_density, angular_frequency) ** 2
        )
        _gyro_freq = find_normalised_gyro_freq(B_total, angular_frequency)
        _gyro_freq_2 = _gyro_freq**2

        self._epsilon_bb = 1 - _plasma_freq_2
        self._epsilon_11 = 1 - _plasma_freq_2 / (1 - _gyro_freq_2)
        self._epsilon_12 = _plasma_freq_2 * _gyro_freq / (1 - _gyro_freq_2)

    @property
    def e_bb(self):
        r"""The :math:`\epsilon_{bb}` component"""
        return self._epsilon_bb

    @property
    def e_11(self):
        r"""The :math:`\epsilon_{11}` component"""
        return self._epsilon_11

    @property
    def e_12(self):
        r"""The :math:`\epsilon_{12}` component"""
        return self._epsilon_12


Stencil = Dict[Tuple, float]

FFD1_stencil: Stencil = {(0,): -3 / 2, (1,): 2, (2,): -0.5}
"""Stencil for the first forward-difference"""
FFD2_stencil: Stencil = {(0,): 2, (1,): -5, (2,): 4, (3,): -1}
"""Stencil for the second forward-difference"""
CFD1_stencil: Stencil = {(-1,): -0.5, (1,): 0.5}
"""Stencil for the first central-difference"""
CFD2_stencil: Stencil = {(-1,): 1, (0,): -2, (1,): 1}
"""Stencil for the second central-difference"""
FFD_FFD_stencil: Stencil = {
    (0, 0): 2.25,
    (0, 1): -3,
    (0, 2): 0.75,
    (1, 0): -3,
    (1, 1): 4,
    (1, 2): -1,
    (2, 0): 0.75,
    (2, 1): -1,
    (2, 2): 0.25,
}
"""Stencil for the mixed second forward-difference"""
FFD_CFD_stencil: Stencil = {
    (0, -1): 0.25,
    (0, 0): 1,
    (0, 1): -1.25,
    (1, 0): -2,
    (1, 1): 2,
    (2, -1): -0.25,
    (2, 0): 1,
    (2, 1): -0.75,
}
"""Stencil for the mixed second forward/central-difference"""
CFD_CFD_stencil: Stencil = {
    (1, 1): 0.25,
    (1, -1): -0.25,
    (-1, 1): -0.25,
    (-1, -1): 0.25,
}
"""Stencil for the mixed second central-difference"""


class Hamiltonian:
    r"""Functor to evaluate derivatives of the Hamiltonian, :math:`H`, at a
    given set of points.

    ``Scotty`` calculates derivatives using a grid-free finite difference
    approach. The Hamiltonian is evaluated at, essentially, an arbitrary set of
    points around the location we wish to get the derivatives at. In practice we
    define stencils as relative offsets from a central point, and the evaluation
    points are the product of the spacing in a given direction with the stencil
    offsets. By carefully choosing our stencils and evaluating all of the
    derivatives at once, we can reuse evaluations of :math:`H` between
    derivatives, saving a lot of computation.

    The stencils are defined as a `dict` with a `tuple` of offsets as keys and
    `float` weights as values. For example, the `CFD1_stencil`::

        {(1,): 0.5, (-1,): -0.5}

    defines the second-order first central-difference:

    .. math::

        f' = \frac{f(x + \delta_x) - f(x - \delta_x)}{2\delta_x}

    The keys are tuples so that we can iterate over the offsets for the mixed
    second derivatives.

    The stencils have been chosen to maximise the reuse of Hamiltonian
    evaluations without sacrificing accuracy.

    Parameters
    ----------
    field
        An object describing the magnetic field of the plasma
    launch_angular_frequency
        Angular frequency of the beam
    mode_flag
        Either ``+/-1``, used to determine which mode branch to use
    density_fit
        Function or ``Callable`` parameterising the density
    delta_R
        Finite difference spacing in the ``R`` direction
    delta_Z
        Finite difference spacing in the ``Z`` direction
    delta_K_R
        Finite difference spacing in the ``K_R`` direction
    delta_K_zeta
        Finite difference spacing in the ``K_zeta`` direction
    delta_K_Z
        Finite difference spacing in the ``K_Z`` direction

    """

    def __init__(
        self,
        field: MagneticField,
        launch_angular_frequency: float,
        mode_flag: int,
        density_fit: DensityFitLike,
        delta_R: float,
        delta_Z: float,
        delta_K_R: float,
        delta_K_zeta: float,
        delta_K_Z: float,
    ):
        self.field = field
        self.angular_frequency = launch_angular_frequency
        self.wavenumber_K0 = angular_frequency_to_wavenumber(launch_angular_frequency)
        self.mode_flag = mode_flag
        self.density = density_fit
        self.spacings = {
            "q_R": delta_R,
            "q_Z": delta_Z,
            "K_R": delta_K_R,
            "K_zeta": delta_K_zeta,
            "K_Z": delta_K_Z,
        }

    def __call__(
        self,
        q_R: ArrayLike,
        q_Z: ArrayLike,
        K_R: ArrayLike,
        K_zeta: ArrayLike,
        K_Z: ArrayLike,
    ):
        """Evaluate the Hamiltonian at the given coordinates

        Parameters
        ----------
        q_R : ArrayLike
        q_Z : ArrayLike
        K_R : ArrayLike
        K_zeta : ArrayLike
        K_Z : ArrayLike

        Returns
        -------
        ArrayLike

        """

        K_magnitude = np.sqrt(K_R**2 + (K_zeta / q_R) ** 2 + K_Z**2)
        poloidal_flux = self.field.poloidal_flux(q_R, q_Z)
        electron_density = self.density(poloidal_flux)
        B_R = np.squeeze(self.field.B_R(q_R, q_Z))
        B_T = np.squeeze(self.field.B_T(q_R, q_Z))
        B_Z = np.squeeze(self.field.B_Z(q_R, q_Z))

        B_total = np.sqrt(B_R**2 + B_T**2 + B_Z**2)
        b_hat = np.array([B_R, B_T, B_Z]) / B_total
        K_hat = np.array([K_R, K_zeta / q_R, K_Z]) / K_magnitude

        # square of the mismatch angle
        if np.size(q_R) == 1:
            sin_theta_m_sq = np.dot(b_hat, K_hat) ** 2
        else:  # Vectorised version of find_H
            b_hat = b_hat.T
            K_hat = K_hat.T
            sin_theta_m_sq = contract_special(b_hat, K_hat) ** 2

        epsilon = DielectricTensor(electron_density, self.angular_frequency, B_total)

        Booker_alpha = (epsilon.e_bb * sin_theta_m_sq) + epsilon.e_11 * (
            1 - sin_theta_m_sq
        )
        Booker_beta = (-epsilon.e_11 * epsilon.e_bb * (1 + sin_theta_m_sq)) - (
            epsilon.e_11**2 - epsilon.e_12**2
        ) * (1 - sin_theta_m_sq)
        Booker_gamma = epsilon.e_bb * (epsilon.e_11**2 - epsilon.e_12**2)

        H_discriminant = np.maximum(
            np.zeros_like(Booker_beta),
            (Booker_beta**2 - 4 * Booker_alpha * Booker_gamma),
        )

        return (K_magnitude / self.wavenumber_K0) ** 2 + (
            Booker_beta - self.mode_flag * np.sqrt(H_discriminant)
        ) / (2 * Booker_alpha)

    def derivatives(
        self,
        q_R: ArrayLike,
        q_Z: ArrayLike,
        K_R: ArrayLike,
        K_zeta: ArrayLike,
        K_Z: ArrayLike,
        second_order: bool = False,
    ) -> Dict[str, ArrayLike]:
        """Evaluate the first-order derivative in all directions at the given
        point(s), and optionally the second-order ones too

        Parameters
        ----------
        q_R : ArrayLike
        q_Z : ArrayLike
        K_R : ArrayLike
        K_zeta : ArrayLike
        K_Z : ArrayLike
            Coordinates to evaluate the derivatives at
        second_order : bool
            If ``True``, also evaluate the second derivatives

        """

        @dataclass(frozen=True)
        class CoordOffset:
            """Helper class to store relative offsets in a dict"""

            q_R: int = 0
            q_Z: int = 0
            K_R: int = 0
            K_zeta: int = 0
            K_Z: int = 0

        # We cache Hamiltonian evaluations only during this function call
        cache: Dict[CoordOffset, ArrayLike] = {}

        # Capture the location we want the derivatives at
        starts = {"q_R": q_R, "q_Z": q_Z, "K_R": K_R, "K_zeta": K_zeta, "K_Z": K_Z}

        def apply_stencil(dims: Tuple[str, ...], stencil: Stencil) -> ArrayLike:
            """Apply a stencil in set of directions

            Parameters
            ----------
            dims
                Tuple of direction names
            stencil
                Finite difference stencil
            """

            # Collect the relative spacings for the derivative dimensions
            dim_spacings = [self.spacings[dim] for dim in dims]
            # For second order derivatives, remove repeated dimensions
            if len(dims) == 2 and dims[1] == dims[0]:
                dims = (dims[0],)

            result = np.zeros_like(starts["q_R"])

            for stencil_offsets, weight in stencil.items():
                coord_offsets = CoordOffset(**dict(zip(dims, stencil_offsets)))
                try:
                    # See if we've already evaluated H here...
                    H_at_offset = cache[coord_offsets]
                except KeyError:
                    # ...if not, let's do so now
                    offsets = asdict(coord_offsets)
                    # Convert integer offsets to absolute positions
                    coords = {
                        dim: start + offsets[dim] * self.spacings[dim]
                        for dim, start in starts.items()
                    }
                    # Evaluate the derivative at this offset and cache it
                    H_at_offset = self(**coords)
                    cache[coord_offsets] = H_at_offset

                result += weight * H_at_offset
            return result / np.prod(dim_spacings)

        # We always compute the first order derivatives
        derivatives = {
            "dH_dR": apply_stencil(("q_R",), FFD1_stencil),
            "dH_dZ": apply_stencil(("q_Z",), FFD1_stencil),
            "dH_dKR": apply_stencil(("K_R",), CFD1_stencil),
            "dH_dKzeta": apply_stencil(("K_zeta",), CFD1_stencil),
            "dH_dKZ": apply_stencil(("K_Z",), CFD1_stencil),
        }

        if second_order:
            second_derivatives = {
                "d2H_dR2": apply_stencil(("q_R", "q_R"), FFD2_stencil),
                "d2H_dZ2": apply_stencil(("q_Z", "q_Z"), FFD2_stencil),
                "d2H_dKR2": apply_stencil(("K_R", "K_R"), CFD2_stencil),
                "d2H_dKzeta2": apply_stencil(("K_zeta", "K_zeta"), CFD2_stencil),
                "d2H_dKZ2": apply_stencil(("K_Z", "K_Z"), CFD2_stencil),
                "d2H_dR_dZ": apply_stencil(("q_R", "q_Z"), FFD_FFD_stencil),
                "d2H_dR_dKR": apply_stencil(("q_R", "K_R"), FFD_CFD_stencil),
                "d2H_dR_dKzeta": apply_stencil(("q_R", "K_zeta"), FFD_CFD_stencil),
                "d2H_dR_dKZ": apply_stencil(("q_R", "K_Z"), FFD_CFD_stencil),
                "d2H_dZ_dKR": apply_stencil(("q_Z", "K_R"), FFD_CFD_stencil),
                "d2H_dZ_dKzeta": apply_stencil(("q_Z", "K_zeta"), FFD_CFD_stencil),
                "d2H_dZ_dKZ": apply_stencil(("q_Z", "K_Z"), FFD_CFD_stencil),
                "d2H_dKR_dKZ": apply_stencil(("K_R", "K_Z"), CFD_CFD_stencil),
                "d2H_dKR_dKzeta": apply_stencil(("K_R", "K_zeta"), CFD_CFD_stencil),
                "d2H_dKzeta_dKZ": apply_stencil(("K_zeta", "K_Z"), CFD_CFD_stencil),
            }
            derivatives.update(second_derivatives)
        return derivatives


def hessians(dH: dict):
    r"""Compute the elements of the Hessian of the Hamiltonian:

    .. math::
          \begin{gather}
            \nabla \nabla H \\
            \nabla_K \nabla H \\
            \nabla_K \nabla_K H \\
          \end{gather}

    given a ``dict`` containing the second derivatives of the Hamiltonian (as
    returned from `Hamiltonian.derivatives` with ``second_order=True``)
    """

    d2H_dR2 = dH["d2H_dR2"]
    d2H_dZ2 = dH["d2H_dZ2"]
    d2H_dKR2 = dH["d2H_dKR2"]
    d2H_dKzeta2 = dH["d2H_dKzeta2"]
    d2H_dKZ2 = dH["d2H_dKZ2"]
    d2H_dR_dZ = dH["d2H_dR_dZ"]
    d2H_dKR_dR = dH["d2H_dR_dKR"]
    d2H_dKzeta_dR = dH["d2H_dR_dKzeta"]
    d2H_dKZ_dR = dH["d2H_dR_dKZ"]
    d2H_dKR_dZ = dH["d2H_dZ_dKR"]
    d2H_dKzeta_dZ = dH["d2H_dZ_dKzeta"]
    d2H_dKZ_dZ = dH["d2H_dZ_dKZ"]
    d2H_dKR_dKZ = dH["d2H_dKR_dKZ"]
    d2H_dKR_dKzeta = dH["d2H_dKR_dKzeta"]
    d2H_dKzeta_dKZ = dH["d2H_dKzeta_dKZ"]

    zeros = np.zeros_like(d2H_dR2)

    def reshape(array: FloatArray):
        """Such that shape is [points,3,3] instead of [3,3,points]"""
        if array.ndim == 2:
            return array
        return np.moveaxis(np.squeeze(array), 2, 0)

    grad_grad_H = reshape(
        np.array(
            [
                [d2H_dR2, zeros, d2H_dR_dZ],
                [zeros, zeros, zeros],
                [d2H_dR_dZ, zeros, d2H_dZ2],
            ]
        )
    )
    gradK_grad_H = reshape(
        np.array(
            [
                [d2H_dKR_dR, zeros, d2H_dKR_dZ],
                [d2H_dKzeta_dR, zeros, d2H_dKzeta_dZ],
                [d2H_dKZ_dR, zeros, d2H_dKZ_dZ],
            ]
        )
    )
    gradK_gradK_H = reshape(
        np.array(
            [
                [d2H_dKR2, d2H_dKR_dKzeta, d2H_dKR_dKZ],
                [d2H_dKR_dKzeta, d2H_dKzeta2, d2H_dKzeta_dKZ],
                [d2H_dKR_dKZ, d2H_dKzeta_dKZ, d2H_dKZ2],
            ]
        )
    )
    return grad_grad_H, gradK_grad_H, gradK_gradK_H
