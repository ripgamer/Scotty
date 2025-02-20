# -*- coding: utf-8 -*-
# Copyright 2022 - 2023, Valerian Hall-Chen and the Scotty contributors
# SPDX-License-Identifier: GPL-3.0

"""Checks input arguments of `beam_me_up <scotty.beam_me_up.beam_me_up>`"""

from __future__ import annotations

from .typing import FloatArray
from .geometry import MagneticField


def check_mode_flag(mode_flag: int) -> None:
    """Mode flag should be either -1 (X-mode) or 1 (O-mode)"""

    if mode_flag not in [-1, 1]:
        raise ValueError(
            f"Bad value for `mode_flag`! Expected either 1 or -1, got '{mode_flag}'"
        )


def check_launch_position(
    poloidal_flux_enter: float, launch_position: FloatArray, field: MagneticField
) -> None:
    R, _, Z = launch_position
    launch_psi = field.poloidal_flux(R, Z)

    if launch_psi < poloidal_flux_enter:
        raise ValueError(
            f"Launch position (R={R:.4f}, Z={Z:.4f}, psi={launch_psi:.4f}) is inside plasma (psi={poloidal_flux_enter})"
        )


def check_input(
    mode_flag: int,
    poloidal_flux_enter: float,
    launch_position: FloatArray,
    field: MagneticField,
) -> None:
    check_mode_flag(mode_flag)
    check_launch_position(poloidal_flux_enter, launch_position, field)
