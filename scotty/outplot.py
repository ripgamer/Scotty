#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr  8 16:15:32 2023

@author: yvonne
"""

import numpy as np
import matplotlib.pyplot as plt
from scotty.fun_general import find_q_lab_Cartesian, find_nearest, contract_special
from scotty.fun_general import (
    find_normalised_plasma_freq,
    find_normalised_gyro_freq,
    make_unit_vector_from_cross_product,
)
from scipy import constants

data_path = "/Users/yvonne/Documents/GitHub/Scotty/results/"
plot_path = data_path


class outplot(object):
    """
    Class that loads outputs from Scotty_main running beam_me_up to make plots.
    Input:
        Path to Scotty_main outputs, input_path (str)
        Suffix to Scotty_main outputs, suffix (str)
        Path to save plots, output_path (str)
    Output:
        None
    """

    # def __new__(cls):
    # print ("__new__ magic method is called")
    # inst = object.__new__(cls)
    # return inst

    def __init__(self, input_path="", suffix="", output_path=""):
        # Path specifics
        self.input_path = input_path
        self.suffix = suffix
        self.output_path = output_path

        # Load data_output
        loadfile = np.load(self.input_path + "data_output" + suffix + ".npz")
        self.q_R_array = loadfile["q_R_array"]
        self.q_zeta_array = loadfile["q_zeta_array"]
        self.q_Z_array = loadfile["q_Z_array"]
        self.K_R_array = loadfile["K_R_array"]
        self.K_Z_array = loadfile["K_Z_array"]
        self.Psi_3D_output = loadfile["Psi_3D_output"]
        self.g_hat_output = loadfile["g_hat_output"]
        self.b_hat_output = loadfile["b_hat_output"]
        self.epsilon_para_output = loadfile["epsilon_para_output"]
        self.epsilon_perp_output = loadfile["epsilon_perp_output"]
        self.epsilon_g_output = loadfile["epsilon_g_output"]
        self.B_magnitude = loadfile["B_magnitude"]
        self.g_magnitude_output = loadfile["g_magnitude_output"]
        self.electron_density_output = loadfile["electron_density_output"]
        self.poloidal_flux_output = loadfile["poloidal_flux_output"]
        self.H_output = loadfile["H_output"]
        loadfile.close()

        # Load analysis_output
        loadfile = np.load(self.input_path + "analysis_output" + suffix + ".npz")
        self.Psi_3D_Cartesian = loadfile["Psi_3D_Cartesian"]
        self.Psi_xx_output = loadfile["Psi_xx_output"]
        self.Psi_xy_output = loadfile["Psi_xy_output"]
        self.Psi_yy_output = loadfile["Psi_yy_output"]
        self.M_xx_output = loadfile["M_xx_output"]
        self.M_xy_output = loadfile["M_xy_output"]
        self.xhat_dot_grad_bhat_dot_xhat_output = loadfile[
            "xhat_dot_grad_bhat_dot_xhat_output"
        ]
        self.xhat_dot_grad_bhat_dot_ghat_output = loadfile[
            "xhat_dot_grad_bhat_dot_ghat_output"
        ]
        self.yhat_dot_grad_bhat_dot_ghat_output = loadfile[
            "yhat_dot_grad_bhat_dot_ghat_output"
        ]
        self.d_theta_d_tau = loadfile["d_theta_d_tau"]
        self.d_xhat_d_tau_dot_yhat_output = loadfile["d_xhat_d_tau_dot_yhat_output"]
        self.kappa_dot_xhat_output = loadfile["kappa_dot_xhat_output"]
        self.kappa_dot_yhat_output = loadfile["kappa_dot_yhat_output"]
        self.distance_along_line = loadfile["distance_along_line"]
        self.cutoff_index = loadfile["cutoff_index"]
        self.R_midplane_points = loadfile["R_midplane_points"]
        self.poloidal_flux_on_midplane = loadfile["poloidal_flux_on_midplane"]
        self.theta_output = loadfile["theta_output"]
        self.theta_m_output = loadfile["theta_m_output"]
        self.delta_theta_m = loadfile["delta_theta_m"]
        self.K_magnitude_array = loadfile["K_magnitude_array"]
        self.k_perp_1_bs = loadfile["k_perp_1_bs"]
        self.loc_b_r_s = loadfile["loc_b_r_s"]
        self.loc_b_r = loadfile["loc_b_r"]
        loadfile.close()

        # Load data_input
        loadfile = np.load(self.input_path + "data_input" + suffix + ".npz")
        self.poloidalFlux_grid = loadfile["poloidalFlux_grid"]
        self.data_R_coord = loadfile["data_R_coord"]
        self.data_Z_coord = loadfile["data_Z_coord"]
        self.launch_position = loadfile["launch_position"]
        self.launch_freq_GHz = loadfile["launch_freq_GHz"]
        loadfile.close()

        # Other values
        self.l_lc = (
            self.distance_along_line - self.distance_along_line[self.cutoff_index]
        )  # Distance from cutoff
        [self.q_X_array, self.q_Y_array, self.q_Z_array] = find_q_lab_Cartesian(
            np.array([self.q_R_array, self.q_zeta_array, self.q_Z_array])
        )
        self.out_index = np.size(self.q_R_array)  # numberOfDataPoints

    # def __del__(self, *args, **kwargs):
    # pass

    # def __str__(self, *args, **kwargs):
    # pass

    # def __repr__(self, *args, **kwargs):
    # pass

    def plotout(self, option=0):
        """
        Function to make plots from Scotty_main output loaded into object instance.
        Input:
            Plot option number, option (int)
        Output:
            Plot(s) generated as determined by plot option number.
            Plot saved to output_path, .jpg file (only for option=1 or 2, included when option=0)
        """
        if option == 0:
            for opt in range(1, 16):
                self.plotout(option=opt)

        elif option == 1:
            ## For plotting the width in the RZ plane
            W_vec_RZ = np.cross(self.g_hat_output, np.array([0, 1, 0]))
            W_vec_RZ_magnitude = np.linalg.norm(W_vec_RZ, axis=1)
            W_uvec_RZ = np.zeros_like(W_vec_RZ)  # Unit vector
            W_uvec_RZ[:, 0] = W_vec_RZ[:, 0] / W_vec_RZ_magnitude
            W_uvec_RZ[:, 1] = W_vec_RZ[:, 1] / W_vec_RZ_magnitude
            W_uvec_RZ[:, 2] = W_vec_RZ[:, 2] / W_vec_RZ_magnitude
            width_RZ = np.sqrt(
                2
                / np.imag(
                    contract_special(
                        W_uvec_RZ, contract_special(self.Psi_3D_output, W_uvec_RZ)
                    )
                )
            )
            W_line_RZ_1_Rpoints = self.q_R_array + W_uvec_RZ[:, 0] * width_RZ
            W_line_RZ_1_Zpoints = self.q_Z_array + W_uvec_RZ[:, 2] * width_RZ
            W_line_RZ_2_Rpoints = self.q_R_array - W_uvec_RZ[:, 0] * width_RZ
            W_line_RZ_2_Zpoints = self.q_Z_array - W_uvec_RZ[:, 2] * width_RZ
            ##

            plt.figure(figsize=(5, 5))
            plt.title("Poloidal Plane")
            contour_levels = np.linspace(0, 1, 11)
            CS = plt.contour(
                self.data_R_coord,
                self.data_Z_coord,
                np.transpose(self.poloidalFlux_grid),
                contour_levels,
                vmin=0,
                vmax=1.2,
                cmap="inferno",
            )
            plt.clabel(
                CS,
                inline=True,
                fontsize=10,
                inline_spacing=-5,
                fmt="%1.1f",
                use_clabeltext=True,
            )  # Labels the flux surfaces
            plt.plot(
                self.q_R_array[: self.out_index], self.q_Z_array[: self.out_index], "k"
            )
            plt.plot(
                [self.launch_position[0], self.q_R_array[0]],
                [self.launch_position[2], self.q_Z_array[0]],
                ":k",
            )
            plt.plot(
                W_line_RZ_1_Rpoints[: self.out_index],
                W_line_RZ_1_Zpoints[: self.out_index],
                "k--",
            )
            plt.plot(
                W_line_RZ_2_Rpoints[: self.out_index],
                W_line_RZ_2_Zpoints[: self.out_index],
                "k--",
            )
            plt.xlim(self.data_R_coord[0], self.data_R_coord[-1])
            plt.ylim(self.data_Z_coord[0], self.data_Z_coord[-1])

            plt.xlabel("R / m")
            plt.ylabel("Z / m")
            plt.tight_layout(pad=1.08, h_pad=None, w_pad=None, rect=None)
            plt.gca().set_aspect("equal", adjustable="box")
            plt.savefig(self.output_path + "propagation_poloidal.jpg", dpi=200)

        elif option == 2:
            ## For plotting the plasma in the toroidal plane
            index_polmin = find_nearest(self.poloidal_flux_on_midplane, 0)
            R_polmin = self.R_midplane_points[index_polmin]
            R_outboard = self.R_midplane_points[
                find_nearest(self.poloidal_flux_on_midplane[index_polmin:], 1)
                + index_polmin
            ]
            index_local_polmax = find_nearest(
                self.poloidal_flux_on_midplane[0:index_polmin], 10
            )
            R_inboard = self.R_midplane_points[
                find_nearest(
                    self.poloidal_flux_on_midplane[index_local_polmax:index_polmin], 1
                )
                + index_local_polmax
            ]
            zeta_plot = np.linspace(-np.pi, np.pi, 1001)
            circle_outboard = np.zeros([1001, 2])
            circle_polmin = np.zeros([1001, 2])
            circle_inboard = np.zeros([1001, 2])
            circle_outboard[:, 0], circle_outboard[:, 1], _ = find_q_lab_Cartesian(
                np.array(
                    [
                        R_outboard * np.ones_like(zeta_plot),
                        zeta_plot,
                        np.zeros_like(zeta_plot),
                    ]
                )
            )
            circle_polmin[:, 0], circle_polmin[:, 1], _ = find_q_lab_Cartesian(
                np.array(
                    [
                        R_polmin * np.ones_like(zeta_plot),
                        zeta_plot,
                        np.zeros_like(zeta_plot),
                    ]
                )
            )
            circle_inboard[:, 0], circle_inboard[:, 1], _ = find_q_lab_Cartesian(
                np.array(
                    [
                        R_inboard * np.ones_like(zeta_plot),
                        zeta_plot,
                        np.zeros_like(zeta_plot),
                    ]
                )
            )
            ##
            ## For plotting how the beam propagates from launch to entry
            (
                launch_position_X,
                launch_position_Y,
                launch_position_Z,
            ) = find_q_lab_Cartesian(self.launch_position)
            entry_position_X, entry_position_Y, entry_position_Z = find_q_lab_Cartesian(
                np.array([self.q_R_array[0], self.q_zeta_array[0], self.q_Z_array[0]])
            )
            ##
            ## For plotting the width in the XY plane
            g_hat_Cartesian = np.zeros([self.out_index, 3])
            g_hat_Cartesian[:, 0] = self.g_hat_output[:, 0] * np.cos(
                self.q_zeta_array
            ) - self.g_hat_output[:, 1] * np.sin(self.q_zeta_array)
            g_hat_Cartesian[:, 1] = self.g_hat_output[:, 0] * np.sin(
                self.q_zeta_array
            ) + self.g_hat_output[:, 1] * np.cos(self.q_zeta_array)
            g_hat_Cartesian[:, 2] = self.g_hat_output[:, 2]

            W_uvec_XY = make_unit_vector_from_cross_product(
                g_hat_Cartesian, np.array([0, 0, 1])
            )
            width_XY = np.sqrt(
                2
                / np.imag(
                    contract_special(
                        W_uvec_XY, contract_special(self.Psi_3D_Cartesian, W_uvec_XY)
                    )
                )
            )
            W_line_XY_1_Xpoints = self.q_X_array + W_uvec_XY[:, 0] * width_XY
            W_line_XY_1_Ypoints = self.q_Y_array + W_uvec_XY[:, 1] * width_XY
            W_line_XY_2_Xpoints = self.q_X_array - W_uvec_XY[:, 0] * width_XY
            W_line_XY_2_Ypoints = self.q_Y_array - W_uvec_XY[:, 1] * width_XY
            ##

            plt.figure(figsize=(5, 5))
            plt.title("Toroidal Plane")
            plt.plot(circle_outboard[:, 0], circle_outboard[:, 1], "orange")
            plt.plot(circle_polmin[:, 0], circle_polmin[:, 1], "#00003F")
            plt.plot(circle_inboard[:, 0], circle_inboard[:, 1], "orange")
            plt.plot(
                self.q_X_array[: self.out_index], self.q_Y_array[: self.out_index], "k"
            )
            plt.plot(
                [launch_position_X, entry_position_X],
                [launch_position_Y, entry_position_Y],
                ":k",
            )
            plt.plot(
                W_line_XY_1_Xpoints[: self.out_index],
                W_line_XY_1_Ypoints[: self.out_index],
                "r--",
            )
            plt.plot(
                W_line_XY_2_Xpoints[: self.out_index],
                W_line_XY_2_Ypoints[: self.out_index],
                "g--",
            )
            plt.xlim(-self.data_R_coord[-1], self.data_R_coord[-1])
            plt.ylim(-self.data_R_coord[-1], self.data_R_coord[-1])
            plt.xlabel("X / m")
            plt.ylabel("Y / m")
            plt.gca().set_aspect("equal", adjustable="box")
            plt.savefig(self.output_path + "propagation_toroidal.jpg", dpi=200)

        elif option == 3:
            plt.figure()
            plt.plot(self.l_lc, self.poloidal_flux_output)

        elif option == 4:
            plt.figure()
            plt.plot(self.l_lc, self.electron_density_output)

        elif option == 5:
            plt.figure()
            plt.subplot(1, 3, 1)
            plt.plot(self.l_lc, self.K_R_array, "k")
            plt.subplot(1, 3, 2)
            plt.plot(self.l_lc, self.K_Z_array, "k")
            plt.subplot(1, 3, 3)
            plt.plot(self.l_lc, self.K_magnitude_array, "k")

        elif option == 6:
            plt.figure()
            plt.subplot(1, 3, 1)
            plt.plot(self.l_lc, self.b_hat_output[:, 0] * self.B_magnitude, "k")
            plt.subplot(1, 3, 2)
            plt.plot(self.l_lc, self.b_hat_output[:, 1] * self.B_magnitude, "k")
            plt.subplot(1, 3, 3)
            plt.plot(self.l_lc, self.b_hat_output[:, 2] * self.B_magnitude, "k")

        elif option == 7:
            plt.figure(figsize=(16, 5))

            plt.subplot(2, 3, 1)
            plt.plot(self.l_lc, np.real(self.Psi_xx_output), "k")
            plt.plot(self.l_lc, np.real(self.M_xx_output), "r")
            plt.title(r"Re$(\Psi_{xx})$ and Re$(M_{xx})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 2)
            plt.plot(self.l_lc, np.real(self.Psi_xy_output), "k")
            plt.plot(self.l_lc, np.real(self.M_xy_output), "r")
            plt.title(r"Re$(\Psi_{xy})$ and Re$(M_{xy})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 3)
            plt.plot(self.l_lc, np.real(self.Psi_yy_output), "k")
            plt.title(r"Re$(\Psi_{yy})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 4)
            plt.plot(self.l_lc, np.imag(self.Psi_xx_output), "k")
            plt.plot(self.l_lc, np.imag(self.M_xx_output), "r")
            plt.title(r"Im$(\Psi_{xx})$ and Im$(M_{xx})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 5)
            plt.plot(self.l_lc, np.imag(self.Psi_xy_output), "k")
            plt.plot(self.l_lc, np.imag(self.M_xy_output), "r")
            plt.title(r"Im$(\Psi_{xy})$ and Im$(M_{xy})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 6)
            plt.plot(self.l_lc, np.imag(self.Psi_yy_output), "k")
            plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
            plt.title(r"Im$(\Psi_{yy})$")
            plt.xlabel(r"$l-l_c$")

        elif option == 8:
            plt.figure(figsize=(10, 5))
            plt.plot(self.l_lc, -2 * self.K_magnitude_array, label="Bragg")
            plt.plot(self.l_lc, self.k_perp_1_bs, label="Full Bragg")
            plt.legend()

        elif option == 9:
            plt.figure()

            plt.subplot(1, 2, 1)
            plt.plot(self.l_lc, self.kappa_dot_xhat_output)
            plt.title(r"$\kappa \cdot \hat{x}$")

            plt.subplot(1, 2, 2)
            plt.plot(self.l_lc, self.kappa_dot_yhat_output)
            plt.title(r"$\kappa \cdot \hat{y}$")

        elif option == 10:
            plt.figure()

            plt.subplot(1, 2, 1)
            plt.plot(
                self.l_lc,
                np.real(self.Psi_xx_output) / (self.k_perp_1_bs / 2),
                "k",
                label=r"$Real (\Psi_{xx}) / (k_1 / 2)$",
            )
            plt.plot(
                self.l_lc,
                self.xhat_dot_grad_bhat_dot_ghat_output,
                label=r"$\hat{x} \cdot \nabla \hat{b} \cdot \hat{g} $",
            )
            plt.plot(
                self.l_lc,
                -self.xhat_dot_grad_bhat_dot_xhat_output * np.tan(self.theta_output),
                label=r"$- \hat{x} \cdot \nabla \hat{b} \cdot \hat{x} \tan \theta$",
            )
            plt.plot(
                self.l_lc,
                (np.sin(self.theta_output) / self.g_magnitude_output)
                * self.d_theta_d_tau,
                label=r"$\sin \theta g d \theta / d \tau$",
            )
            plt.plot(
                self.l_lc,
                -self.kappa_dot_xhat_output * np.sin(self.theta_output),
                label=r"$-\kappa \cdot \hat{x} \sin \theta$",
            )
            plt.xlabel(r"$(l - l_c)$")
            plt.legend(loc="center right", bbox_to_anchor=(-0.2, 0.5))

            plt.subplot(1, 2, 2)
            plt.plot(
                self.l_lc,
                np.real(self.Psi_xy_output) / (self.k_perp_1_bs / 2),
                "k",
                label=r"$Real (\Psi_{xy}) / (k_1 / 2)$",
            )
            plt.plot(
                self.l_lc,
                -self.kappa_dot_yhat_output * np.sin(self.theta_output),
                label=r"$-\kappa \cdot \hat{y} \sin \theta$",
            )
            plt.plot(
                self.l_lc,
                self.yhat_dot_grad_bhat_dot_ghat_output,
                label=r"$\hat{y} \cdot \nabla \hat{b} \cdot \hat{g}$",
            )
            plt.plot(
                self.l_lc,
                (
                    np.sin(self.theta_output)
                    * np.tan(self.theta_output)
                    / self.g_magnitude_output
                )
                * self.d_xhat_d_tau_dot_yhat_output,
                label=r"$d \hat{x} / d \tau \cdot \hat{y} \sin \theta \tan \theta / g$",
            )
            plt.xlabel(r"$(l - l_c)$")
            plt.legend(loc="center left", bbox_to_anchor=(1, 0.5))

        elif option == 11:
            loc_m = np.exp(-2 * (self.theta_m_output / self.delta_theta_m) ** 2)

            plt.figure()

            plt.subplot(3, 2, 1)
            plt.title("mismatch")
            plt.plot(self.l_lc, np.rad2deg(self.theta_m_output), label=r"$\theta_m$")
            plt.plot(
                self.l_lc, np.rad2deg(self.delta_theta_m), label=r"$\Delta \theta_m$"
            )
            plt.legend()
            plt.xlabel(r"$(l - l_c)$")
            plt.ylabel("deg")

            plt.subplot(3, 2, 2)
            plt.plot(self.l_lc, loc_m, label="loc_m")
            plt.xlabel(r"$(l - l_c)$")
            plt.legend()

            plt.subplot(3, 2, 3)
            plt.plot(self.l_lc, self.loc_b_r, label="loc_b_r")
            plt.xlabel(r"$(l - l_c)$")
            plt.legend()

            plt.subplot(3, 2, 4)
            plt.plot(self.l_lc, self.loc_b_r_s, label="loc_b_r_s")
            plt.xlabel(r"$(l - l_c)$")
            plt.legend()

            plt.subplot(3, 2, 5)
            plt.plot(self.l_lc, self.loc_b_r * loc_m, label="loc_b_m_r")
            plt.xlabel(r"$(l - l_c)$")
            plt.legend()

            plt.subplot(3, 2, 6)
            plt.plot(self.l_lc, self.loc_b_r_s * loc_m, label="loc_b_m_r_s")
            plt.xlabel(r"$(l - l_c)$")
            plt.legend()

        elif option == 12:
            plt.figure()
            plt.title("H (Booker quartic)")
            plt.plot(self.l_lc, self.H_output)

        elif option == 13:
            plt.figure(figsize=(16, 5))

            plt.subplot(2, 3, 1)
            plt.plot(self.l_lc, np.real(self.Psi_xx_output), "k")
            plt.plot(self.l_lc, np.real(self.M_xx_output), "r")
            plt.title(r"Re$(\Psi_{xx})$ and Re$(M_{xx})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 2)
            plt.plot(self.l_lc, np.real(self.Psi_xy_output), "k")
            plt.plot(self.l_lc, np.real(self.M_xy_output), "r")
            plt.title(r"Re$(\Psi_{xy})$ and Re$(M_{xy})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 3)
            plt.plot(self.l_lc, np.real(self.Psi_yy_output), "k")
            plt.title(r"Re$(\Psi_{yy})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 4)
            plt.plot(self.l_lc, np.imag(self.Psi_xx_output), "k")
            plt.plot(self.l_lc, np.imag(self.M_xx_output), "r")
            plt.title(r"Im$(\Psi_{xx})$ and Im$(M_{xx})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 5)
            plt.plot(self.l_lc, np.imag(self.Psi_xy_output), "k")
            plt.plot(self.l_lc, np.imag(self.M_xy_output), "r")
            plt.title(r"Im$(\Psi_{xy})$ and Im$(M_{xy})$")
            plt.xlabel(r"$l-l_c$")

            plt.subplot(2, 3, 6)
            plt.plot(self.l_lc, np.imag(self.Psi_yy_output), "k")
            plt.tight_layout(pad=0.4, w_pad=0.5, h_pad=1.0)
            plt.title(r"Im$(\Psi_{yy})$")
            plt.xlabel(r"$l-l_c$")

        elif option == 14:
            plt.figure()
            plt.plot(self.l_lc, np.rad2deg(self.theta_output), label="theta")
            plt.plot(self.l_lc, np.rad2deg(self.theta_m_output), label="theta m")
            plt.plot(self.l_lc, np.rad2deg(self.delta_theta_m), label="delta theta m")
            plt.legend()
            plt.xlabel(r"$(l - l_c)$")
            plt.ylabel("deg")

        elif option == 15:
            factor = -1 - self.theta_output / self.theta_m_output

            launch_angular_frequency = 2e9 * np.pi * self.launch_freq_GHz
            wavenumber_K0 = launch_angular_frequency / constants.c

            om_pe_norm = find_normalised_plasma_freq(
                self.electron_density_output, launch_angular_frequency
            )
            om_ce_norm = find_normalised_gyro_freq(
                self.B_magnitude, launch_angular_frequency
            )

            # K_mag = self.K_magnitude_array
            # eps_11 = self.epsilon_perp_output
            # eps_12 = self.epsilon_g_output
            # eps_bb = self.epsilon_para_output
            N_sq = (self.K_magnitude_array / wavenumber_K0) ** 2

            factor2 = (
                self.epsilon_perp_output**2
                - self.epsilon_g_output**2
                - self.epsilon_perp_output * self.epsilon_para_output
                - self.epsilon_perp_output * N_sq
                + self.epsilon_para_output * N_sq
            ) / (
                -(self.epsilon_perp_output**2)
                + self.epsilon_g_output**2
                - self.epsilon_perp_output * self.epsilon_para_output
                + self.epsilon_perp_output * N_sq * 2
            )

            factor_O = -(om_pe_norm**2)

            factor_X = (om_pe_norm**2 * (1 - om_pe_norm**2)) / (
                1 - om_pe_norm**2 - om_ce_norm**2
            )

            plt.figure()
            plt.plot(self.l_lc, factor, "ko", label="-1 - theta / theta_m")
            plt.plot(self.l_lc, factor2, label="Either mode")
            plt.plot(self.l_lc, factor_O, label="O mode")
            plt.plot(self.l_lc, factor_X, label="X mode")
            plt.legend()
            plt.xlabel("l - l_c")

        else:
            raise ValueError(
                "Plot option must be 0 (generate all plots) or integer from 1-15"
            )
