# -*- coding: utf-8 -*-
"""
Created on Fri Jun  8 10:44:34 2018

@author: VH Hall-Chen
Valerian Hongjie Hall-Chen
valerian@hall-chen.com


For shot 29908, the EFIT++ times are efit_times = np.linspace(0.155,0.25,20)
I want efit_times[np.arange(0,10)*2 + 1]. 160ms, 170ms, ..., 250ms
"""
from scotty.beam_me_up import beam_me_up
from scotty.fun_general import (
    find_q_lab_Cartesian,
    find_q_lab,
    find_K_lab_Cartesian,
    find_K_lab,
    find_waist,
    find_Rayleigh_length,
    genray_angles_from_mirror_angles,
)
from scotty.fun_general import propagate_beam

from scipy import constants
import math
import numpy as np
import sys
import os

from scotty.init_bruv import get_parameters_for_Scotty


equil_times = np.array([0.15])
poloidal_launch_angles_Torbeam = np.array([-2.5])
toroidal_launch_angles_Torbeam = np.array([3.0])
# toroidal_launch_angles_Torbeam = np.linspace(-5,5,101)
# launch_freqs_GHz = np.array([30.0])
launch_freqs_GHz = np.array([32.5, 35, 37.5, 40, 42.5, 45, 47.5, 50])

total_simulations = (
    len(equil_times)
    * len(poloidal_launch_angles_Torbeam)
    * len(toroidal_launch_angles_Torbeam)
    * len(launch_freqs_GHz)
)
counter = 0
for ii, equil_time in enumerate(equil_times):
    for jj, poloidal_launch_angle_Torbeam in enumerate(poloidal_launch_angles_Torbeam):
        for kk, toroidal_launch_angle_Torbeam in enumerate(
            toroidal_launch_angles_Torbeam
        ):
            for ll, launch_freq_GHz in enumerate(launch_freqs_GHz):

                kwargs_dict = get_parameters_for_Scotty(
                    "DBS_UCLA_MAST-U",
                    launch_freq_GHz=launch_freq_GHz,
                    find_B_method="test",  # EFITpp, UDA_saved, UDA, torbeam
                    user="Valerian_desktop",
                )

                kwargs_dict["mode_flag"] = -1
                kwargs_dict[
                    "poloidal_launch_angle_Torbeam"
                ] = poloidal_launch_angle_Torbeam
                kwargs_dict[
                    "toroidal_launch_angle_Torbeam"
                ] = toroidal_launch_angle_Torbeam

                kwargs_dict["shot"] = 45290  # To load the EFIT output
                kwargs_dict["equil_time"] = equil_time  # To load the EFIT output

                if kwargs_dict["mode_flag"] == 1:
                    mode_string = "O"
                elif kwargs_dict["mode_flag"] == -1:
                    mode_string = "X"

                kwargs_dict["output_filename_suffix"] = (
                    "_pol"
                    + f"{poloidal_launch_angle_Torbeam:.1f}"
                    + "_tor"
                    + f"{toroidal_launch_angle_Torbeam:.1f}"
                    + "_f"
                    + f"{launch_freq_GHz:.1f}"
                    + "_"
                    + mode_string
                    + "_"
                    + f"{equil_time*1000:.3g}"
                    + "ms"
                )

                kwargs_dict["quick_run"] = False
                kwargs_dict["figure_flag"] = False
                kwargs_dict[
                    "output_path"
                ] = "D:\\Dropbox\\VHChen2021\\Data - Scotty\\Run 29\\"
                kwargs_dict["density_fit_parameters"] = None
                kwargs_dict[
                    "ne_data_path"
                ] = "D:\\Dropbox\\VHChen2021\\Data - Equilibrium\MAST-U\\"
                kwargs_dict[
                    "magnetic_data_path"
                ] = "D:\\Dropbox\\VHChen2021\\Data - Equilibrium\MAST-U\\"
                kwargs_dict["input_filename_suffix"] = (
                    "_shotgroup6_avr_" + f"{equil_time*1000:.0f}" + "ms"
                )

                if equil_time == 0.15:
                    kwargs_dict["poloidal_flux_enter"] = 1.06520296**2
                    # kwargs_dict['Psi_BC_flag'] = False

                kwargs_dict["delta_R"] = -0.00001
                kwargs_dict["delta_Z"] = -0.00001
                kwargs_dict["delta_K_R"] = 0.1
                kwargs_dict["delta_K_zeta"] = 0.1
                kwargs_dict["delta_K_Z"] = 0.1
                kwargs_dict["interp_smoothing"] = 0.0
                kwargs_dict["len_tau"] = 1002
                kwargs_dict["rtol"] = 1e-4
                kwargs_dict["atol"] = 1e-7

                if ii == 0 and jj == 0 and kk == 0 and kk == ll:
                    kwargs_dict["verbose_output_flag"] = True
                else:
                    kwargs_dict["verbose_output_flag"] = False

                data_output = (
                    kwargs_dict["output_path"]
                    + "data_output"
                    + kwargs_dict["output_filename_suffix"]
                    + ".npz"
                )
                analysis_output = (
                    kwargs_dict["output_path"]
                    + "analysis_output"
                    + kwargs_dict["output_filename_suffix"]
                    + ".npz"
                )

                counter = counter + 1

                if os.path.exists(data_output) and os.path.exists(analysis_output):
                    continue
                else:
                    print("simulation ", counter, "of", total_simulations)
                    beam_me_up(**kwargs_dict)

                # beam_me_up(**kwargs_dict)
