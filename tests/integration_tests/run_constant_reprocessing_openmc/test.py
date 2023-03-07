"""Run SaltProc with reprocessing"""
import os
import shutil
from pathlib import Path
import sys

import numpy as np
import pytest

import tables as tb
import subprocess


@pytest.fixture
def setup(scope='module'):
    cwd = Path(__file__).parents[0].resolve()
    os.chdir(cwd)
    test_db = cwd / 'saltproc_runtime/saltproc_results.h5'
    ref_db = cwd / 'msbr_reference_results.h5'
    atol = 3e-3
    rtol = 4e-2

    return cwd, test_db, ref_db, atol, rtol

@pytest.mark.slow
def test_integration_2step_constant_ideal_removal_heavy(setup):
    cwd, test_db, ref_db, atol, rtol = setup
    args = ['python', '-m', 'saltproc', '-i', str(cwd / 'msbr_input.json')]
#    subprocess.run(
#        args,
#        check=True,
#        cwd=cwd,
#        stdout=sys.stdout,
#        stderr=subprocess.STDOUT)
    #np.testing.assert_allclose(read_keff(test_db), read_keff(ref_db), atol=tol)
    assert_db_allclose(test_db, ref_db, atol, rtol)

    #shutil.rmtree(cwd / 'saltproc_runtime')

def read_keff(file):
    db = tb.open_file(file, mode='r')
    sim_param = db.root.simulation_parameters
    # Keff at t=0 depletion step
    k_0 = np.array([x['keff_bds'][0] for x in sim_param.iterrows()])
    k_0_e = np.array([x['keff_bds'][1] for x in sim_param.iterrows()])
    # Keff at t=end depletion step
    k_1 = np.array([x['keff_eds'][0] for x in sim_param.iterrows()])
    k_1_e = np.array([x['keff_eds'][1] for x in sim_param.iterrows()])
    db.close()
    return k_0, k_1, k_0_e, k_1_e

def assert_db_allclose(test_db, ref_db, atol, rtol):
    assert_nuclide_mass_allclose(test_db, ref_db, atol, rtol)
    assert_in_out_streams_allclose(test_db, ref_db, atol, rtol)
    ref_data, ref_param = read_fuel(ref_db)
    test_data, test_param = read_fuel(test_db)
    # Compare materials composition
    for node_nm, node in ref_data.items():
        for nuc, mass_arr in node.items():
            np.testing.assert_allclose(
                mass_arr, test_data[node_nm][nuc], atol=atol, rtol=rtol)
    # Compare material properties
    np.testing.assert_allclose(test_param, ref_param, atol=atol, rtol=rtol)

def assert_nuclide_mass_allclose(test_db, ref_db, atol, rtol):
    ref_mass_before, ref_mass_after = read_nuclide_mass(ref_db)
    test_mass_before, test_mass_after = read_nuclide_mass(test_db)
    for key, val in ref_mass_before.items():
        np.testing.assert_allclose(val, test_mass_before[key], atol=atol, rtol=rtol)
    for key, val in ref_mass_after.items():
        np.testing.assert_allclose(val, test_mass_after[key], atol=atol, rtol=rtol)

def read_nuclide_mass(db_file):
    db = tb.open_file(db_file, mode='r')
    fuel_before = db.root.materials.fuel.before_reproc.comp
    fuel_after = db.root.materials.fuel.after_reproc.comp
    nucmap = fuel_before.attrs.iso_map

    mass_before = {}
    mass_after = {}

    for nuc in nucmap:
        mass_before[nuc] = np.array([row[nucmap[nuc]] for row in fuel_before])
        mass_after[nuc] = np.array([row1[nucmap[nuc]] for row1 in fuel_after])
    db.close()
    return mass_before, mass_after

def assert_in_out_streams_allclose(test_db, ref_db, atol, rtol):
    ref_sparger, \
        ref_test_separator, \
        ref_ni_filter, \
        ref_feed = read_in_out_streams(ref_db)
    test_sparger, \
        test_separator, \
        test_ni_filter, \
        test_feed = read_in_out_streams(test_db)
    for key, val in ref_sparger.items():
        np.testing.assert_allclose(val, test_sparger[key], atol=atol, rtol=rtol)
    for key, val in ref_test_separator.items():
        np.testing.assert_allclose(val, test_separator[key], atol=atol, rtol=rtol)
    for key, val in ref_ni_filter.items():
        np.testing.assert_allclose(val, test_ni_filter[key], atol=atol, rtol=rtol)
    for key, val in ref_feed.items():
        np.testing.assert_allclose(val, test_feed[key], atol=atol, rtol=rtol)

def read_in_out_streams(db_file):
    db = tb.open_file(db_file, mode='r')
    waste_sparger = db.root.materials.fuel.in_out_streams.waste_sparger
    waste_separator = \
        db.root.materials.fuel.in_out_streams.waste_entrainment_separator
    waste_ni_filter = db.root.materials.fuel.in_out_streams.waste_nickel_filter
    feed_leu = db.root.materials.fuel.in_out_streams.feed_leu
    waste_nucmap = waste_ni_filter.attrs.iso_map
    feed_nucmap = feed_leu.attrs.iso_map
    mass_waste_sparger = {}
    mass_waste_separator = {}
    mass_waste_ni_filter = {}
    mass_feed_leu = {}

    for nuc in waste_nucmap:
        mass_waste_sparger[nuc] = np.array(
            [row[waste_nucmap[nuc]] for row in waste_sparger])
        mass_waste_separator[nuc] = np.array(
            [row[waste_nucmap[nuc]] for row in waste_separator])
        mass_waste_ni_filter[nuc] = np.array(
            [row[waste_nucmap[nuc]] for row in waste_ni_filter])
    for nuc in feed_nucmap:
        mass_feed_leu[nuc] = np.array(
            [row[feed_nucmap[nuc]] for row in feed_leu])
    db.close()
    return mass_waste_sparger, \
        mass_waste_separator, \
        mass_waste_ni_filter, \
        mass_feed_leu

def read_fuel(file):
    db = tb.open_file(file, mode='r')
    fuel = db.root.materials.fuel
    out_data = {}
    for node in db.walk_nodes(fuel, classname="EArray"):
        nucmap = node.attrs.iso_map
        out_data[node._v_name] = {}
        # print(node)
        for nuc in nucmap:
            out_data[node._v_name][nuc] = \
                np.array([row[nucmap[nuc]] for row in node])
    # Read table with material parameters (density, temperature, mass)
    tmp = fuel.after_reproc.parameters.read()
    # Convert structured array to simple array
    param = tmp.view(np.float64).reshape(tmp.shape + (-1,))
    db.close()
    return out_data, param