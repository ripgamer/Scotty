from scotty.beam_me_up import beam_me_up, create_magnetic_geometry
from scotty.init_bruv import get_parameters_for_Scotty
from scotty.torbeam import write_torbeam_file, construct_torbeam_field

import json
import numpy as np
from numpy.testing import assert_allclose
import pytest


CUTOFF_INDEX = 5

PSI_START_EXPECTED = np.array(
    [
        [
            -2.47357794e03 + 1.19557806e01j,
            -1.39916828e-02 - 1.43347874e-02j,
            3.40523926e02 - 1.13752568e02j,
        ],
        [
            -1.39916828e-02 - 1.43347874e-02j,
            4.24589207e03 + 4.35001002e03j,
            2.21127206e-03 + 2.26549697e-03j,
        ],
        [
            3.40523926e02 - 1.13752568e02j,
            2.21127206e-03 + 2.26549697e-03j,
            4.25776357e02 + 1.08229209e03j,
        ],
    ]
)
PSI_CUTOFF_EXPECTED = np.array(
    [
        [
            -3415.07623355 + 445.31992622j,
            -282.82924665 - 149.90119128j,
            509.18231115 - 398.50960651j,
        ],
        [
            -282.82924665 - 149.90119128j,
            3929.38936698 + 2642.61848492j,
            -55.70975677 - 74.68041153j,
        ],
        [
            509.18231115 - 398.50960651j,
            -55.70975677 - 74.68041153j,
            2049.26382135 + 377.83003374j,
        ],
    ]
)
PSI_FINAL_EXPECTED = np.array(
    [
        [
            -759.55423192 + 13243.111223j,
            -479.31204769 + 514.09773505j,
            -644.55622419 - 1452.45488266j,
        ],
        [
            -479.31204769 + 514.09773505j,
            3487.94478663 + 1885.63739326j,
            12.71272627 - 77.55460115j,
        ],
        [
            -644.55622419 - 1452.45488266j,
            12.71272627 - 77.55460115j,
            2470.84658744 + 159.68128543j,
        ],
    ]
)


EXPECTED = {
    "q_R_array": np.array(
        [
            1.99382564,
            1.8973136,
            1.82080896,
            1.76044632,
            1.71327164,
            1.69395316,
            1.67708778,
            1.65019221,
            1.63108066,
            1.61859347,
        ]
    ),
    "q_Z_array": np.array(
        [
            -0.07804514,
            -0.09137557,
            -0.10919534,
            -0.13253917,
            -0.1627768,
            -0.18095369,
            -0.20155828,
            -0.25072523,
            -0.3125676,
            -0.3901351,
        ]
    ),
    "q_zeta_array": np.array(
        [
            0.0,
            -0.00041565,
            -0.00168641,
            -0.00380195,
            -0.00660756,
            -0.00815794,
            -0.00972988,
            -0.01265907,
            -0.01496556,
            -0.01641859,
        ]
    ),
    "K_R_array": np.array(
        [
            -1146.40007,
            -909.7351259,
            -718.97020274,
            -564.32641187,
            -437.85637809,
            -383.2161993,
            -333.12907589,
            -245.07498321,
            -169.39921007,
            -102.43869197,
        ]
    ),
    "K_Z_array": np.array(
        [
            -120.49150267,
            -165.72589293,
            -219.64365799,
            -284.80168007,
            -364.33147671,
            -410.55892646,
            -462.07152722,
            -582.78670158,
            -732.58798218,
            -919.20759736,
        ]
    ),
    "K_zeta_initial": np.array(-0.0),
    "tau_array": np.array(
        [
            0.0,
            62.6209717,
            125.2419434,
            187.86291511,
            250.48388681,
            281.73236206,
            313.10485851,
            375.72583021,
            438.34680191,
            500.96777362,
        ]
    ),
    "B_magnitude": np.array(
        [
            0.75898041,
            0.79758802,
            0.83110015,
            0.85959713,
            0.883266,
            0.8933391,
            0.90232283,
            0.91702929,
            0.92777423,
            0.93493185,
        ]
    ),
    "normalised_gyro_freqs": np.array(
        [
            0.38628639,
            0.4059359,
            0.42299204,
            0.43749571,
            0.44954208,
            0.45466883,
            0.45924114,
            0.46672606,
            0.47219474,
            0.47583764,
        ]
    ),
    "normalised_plasma_freqs": np.array(
        [
            0.01388158,
            0.59773859,
            0.75915389,
            0.83777097,
            0.8712485,
            0.87520137,
            0.8712369,
            0.83771518,
            0.7590454,
            0.59751663,
        ]
    ),
}


def simple(path):
    """Built-in synthetic diagnostic"""
    return get_parameters_for_Scotty("DBS_synthetic")


def ne_dat_file(path):
    """Density fit using TORBEAM file"""
    kwargs_dict = get_parameters_for_Scotty("DBS_synthetic")

    ne_filename = path / "ne.dat"
    rho = np.linspace(0, 1)
    density_fit = kwargs_dict["density_fit_method"]
    density = density_fit(rho**2)

    with open(ne_filename, "w") as f:
        f.write(f"{len(rho)}\n")
        np.savetxt(f, np.column_stack((rho, density)), fmt="%.7e")

    kwargs_dict["density_fit_parameters"] = None
    kwargs_dict["density_fit_method"] = "smoothing-spline-file"
    kwargs_dict["ne_data_path"] = path
    return kwargs_dict


def torbeam_file(path):
    """Geometry using TORBEAM file"""
    kwargs_dict = get_parameters_for_Scotty("DBS_synthetic")

    write_torbeam_file(
        major_radius=kwargs_dict["R_axis"],
        minor_radius=kwargs_dict["minor_radius_a"],
        B_toroidal_max=kwargs_dict["B_T_axis"],
        B_poloidal_max=kwargs_dict["B_p_a"],
        buffer_factor=1.1,
        x_grid_length=100,
        z_grid_length=100,
        torbeam_directory_path=path,
    )

    kwargs_dict["find_B_method"] = "torbeam"
    kwargs_dict["magnetic_data_path"] = path
    return kwargs_dict


def omfit_json(path):
    """Geometry using OMFIT JSON file"""
    kwargs_dict = get_parameters_for_Scotty("DBS_synthetic")

    R_grid, Z_grid, B_R, B_t, B_Z, psi = construct_torbeam_field(
        major_radius=kwargs_dict["R_axis"],
        minor_radius=kwargs_dict["minor_radius_a"],
        B_toroidal_max=kwargs_dict["B_T_axis"],
        B_poloidal_max=kwargs_dict["B_p_a"],
        buffer_factor=1.1,
        x_grid_length=100,
        z_grid_length=100,
    )

    def flatten_as_F(array):
        return array.T.flatten().tolist()

    data = {
        "R": R_grid.tolist(),
        "Z": Z_grid.tolist(),
        "Br": flatten_as_F(B_R),
        "Bt": flatten_as_F(B_t),
        "Bz": flatten_as_F(B_Z),
        "pol_flux": flatten_as_F(psi),
    }

    with open(path / "topfile.json", "w") as f:
        json.dump(data, f)

    kwargs_dict["find_B_method"] = "omfit"
    kwargs_dict["magnetic_data_path"] = path
    return kwargs_dict


@pytest.mark.parametrize(
    "generator",
    [
        pytest.param(simple, id="simple"),
        pytest.param(ne_dat_file, id="density-fit-file"),
        pytest.param(torbeam_file, id="torbeam-file"),
        pytest.param(omfit_json, id="omfit-file"),
    ],
)
def test_integrated(tmp_path, generator):
    """Golden answer test to check basic functionality using circular
    flux surfaces."""

    kwargs_dict = generator(tmp_path)
    kwargs_dict["output_filename_suffix"] = "_Bpa0.10"
    kwargs_dict["figure_flag"] = False
    kwargs_dict["len_tau"] = 10
    kwargs_dict["output_path"] = tmp_path

    beam_me_up(**kwargs_dict)

    assert len(list(tmp_path.glob("*.npz"))) == 4

    with np.load(tmp_path / "data_output_Bpa0.10.npz") as f:
        output = dict(f)

    for key, value in EXPECTED.items():
        assert_allclose(output[key], value, rtol=1e-2, err_msg=key)

    K_magnitude = np.hypot(output["K_R_array"], output["K_Z_array"])
    assert K_magnitude.argmin() == CUTOFF_INDEX

    assert_allclose(output["Psi_3D_output"][0, ...], PSI_START_EXPECTED, rtol=1.8e-2)
    assert_allclose(
        output["Psi_3D_output"][CUTOFF_INDEX, ...], PSI_CUTOFF_EXPECTED, rtol=1e-2
    )
    # Slightly larger tolerance here, likely due to floating-point
    # precision of file-based input
    assert_allclose(output["Psi_3D_output"][-1, ...], PSI_FINAL_EXPECTED, rtol=2e-2)


@pytest.mark.parametrize(
    "generator",
    [
        pytest.param(ne_dat_file, id="density-fit-file"),
        pytest.param(torbeam_file, id="torbeam-file"),
        pytest.param(omfit_json, id="omfit-file"),
    ],
)
def test_create_magnetic_geometry(tmp_path, generator):
    kwargs_dict = generator(tmp_path)

    field = create_magnetic_geometry(**kwargs_dict)
    field_golden = create_magnetic_geometry(**simple(tmp_path))

    assert_allclose(
        field.B_R(field.data_R_coord, field.data_Z_coord),
        field_golden.B_R(field.data_R_coord, field.data_Z_coord),
        rtol=1e-6,
    )
    assert_allclose(
        field.B_T(field.data_R_coord, field.data_Z_coord),
        field_golden.B_T(field.data_R_coord, field.data_Z_coord),
        rtol=1e-6,
    )
    assert_allclose(
        field.B_Z(field.data_R_coord, field.data_Z_coord),
        field_golden.B_Z(field.data_R_coord, field.data_Z_coord),
        rtol=1e-6,
    )
    assert_allclose(
        field.poloidal_flux(field.data_R_coord, field.data_Z_coord),
        field_golden.poloidal_flux(field.data_R_coord, field.data_Z_coord),
        rtol=1e-6,
    )
