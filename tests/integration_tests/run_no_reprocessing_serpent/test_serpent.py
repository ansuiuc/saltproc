"""Run SaltProc without reprocessing"""
from pathlib import Path
import shutil

import numpy as np
import pytest

from pyne import serpent
from saltproc import app


@pytest.fixture
def setup():
    cwd = str(Path(__file__).parents[0].resolve())
    saltproc_input = cwd + '/test_input.json'

    input_path, process_input_file, path_input_file, mpi_args, object_input = \
        app.read_main_input(saltproc_input)

    depcode = app._create_depcode_object(object_input[0])

    simulation = app._create_simulation_object(object_input[1], depcode)

    reactor = app._create_reactor_object(object_input[2])

    return cwd, simulation, reactor


@pytest.mark.slow
def test_integration_2step_saltproc_no_reproc_heavy(setup):
    cwd, simulation, reactor = setup
    runsim_no_reproc(simulation, reactor, 2)

    output_path = str(simulation.sim_depcode.output_path)
    ref_result = serpent.parse_dep(cwd + '/reference_dep.m', make_mats=False)
    test_result = serpent.parse_dep(f'{output_path}/runtime_input.serpent_dep.m', make_mats=False)

    ref_mdens_error = np.loadtxt(cwd + '/reference_error')

    ref_fuel_mdens = ref_result['MAT_fuel_MDENS'][:, -2]
    test_fuel_mdens = test_result['MAT_fuel_MDENS'][:, -1]

    test_mdens_error = np.array(ref_fuel_mdens - test_fuel_mdens)
    np.testing.assert_array_almost_equal(test_mdens_error, ref_mdens_error)

    shutil.rmtree(cwd + '/saltproc_runtime')


def runsim_no_reproc(simulation, reactor, nsteps):
    """Run simulation sequence for integration test. No reprocessing
    involved, just re-running depletion code for comparision with model
    output.

    Parameters
    ----------
    simulation : Simulation
        Simulation object
    reactor : Reactor
        Contains information about power load curve and cumulative
        depletion time for the integration test.
    nsteps : int
        Number of depletion time steps in integration test run.

    """

    ######################################################################
    # Start sequence
    for dep_step in range(nsteps):
        print("\nStep #%i has been started" % (dep_step + 1))
        if dep_step == 0:  # First step
            simulation.sim_depcode.write_runtime_input(
                reactor,
                dep_step,
                False)
            simulation.sim_depcode.run_depletion_step()
            # Read general simulation data which never changes
            simulation.store_run_init_info()
            # Parse and store data for initial state (beginning of dep_step)
            mats = simulation.sim_depcode.read_depleted_materials(
                False)
            simulation.store_mat_data(mats, dep_step, False)
        # Finish of First step
        # Main sequence
        else:
            simulation.sim_depcode.run_depletion_step()
        mats = simulation.sim_depcode.read_depleted_materials(
            True)
        simulation.store_mat_data(mats, dep_step, False)
        simulation.store_run_step_info()
        simulation.sim_depcode.update_depletable_materials(
            mats,
            simulation.burn_time)
