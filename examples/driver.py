from saltproc import Depcode
from saltproc import Simulation
from saltproc import Materialflow
from saltproc import Process
# from depcode import Depcode
# from simulation import Simulation
# from materialflow import Materialflow
import os
import tables as tb
import json
from collections import OrderedDict
import gc


input_path = os.path.dirname(os.path.abspath(__file__)) + '/../saltproc/'
# input_path = '/home/andrei2/Desktop/git/saltproc/develop/saltproc'
spc_inp_file = os.path.join(input_path, '../examples/input_1979leu.json')
input_file = os.path.join(input_path, 'data/saltproc_tap')
template_file = os.path.join(input_path, 'data/tap')
iter_matfile = os.path.join(input_path, 'data/saltproc_mat')
db_file = os.path.join(input_path, 'data/db_saltproc.h5')
compression_prop = tb.Filters(complevel=9, complib='blosc', fletcher32=True)
# executable path of Serpent
exec_path = '/home/andrei2/serpent/serpent2/src_2131/sss2'
# exec_path = '/projects/sciteam/bahg/serpent/src2.1.31/sss2'  # BW
restart_flag = True
pc_type = 'pc'  # 'bw', 'falcon'
# Number of cores and nodes to use in cluster
cores = 4  # doesn't used on Falcon (grabbing it from PBS)
nodes = 1  # doesn't use on Falcon (grabbing it from PBS)
steps = 2
# Monte Carlo method parameters
neutron_pop = 6000  # 10 000, 400, 100: 35pcm; 12 000, 400, 200: 31pcm
active_cycles = 100  # 20
inactive_cycles = 60  # 5
# Define materials (should read from input file)
core_massflow_rate = 9.92e+6  # g/s


def read_processes_from_input():
    processes = OrderedDict()
    with open(spc_inp_file) as f:
        j = json.load(f)
        # print(j)
        for mat, value in j.items():
            processes[mat] = OrderedDict()
            for obj_name, obj_data in j[mat]['extraction_processes'].items():
                processes[mat][obj_name] = Process(**obj_data)
        """print(processes)
        print('\nFuel mat', processes['fuel'])
        print('\nPoison rods mat', processes['ctrlPois'])
        print('\nProcess objects attributes:')
        print("Sparger efficiency ", processes['fuel']['sparger'].efficiency)
        # print("Ni filter efficiency", processes['nickel_filter'].efficiency)
        print(processes['fuel']['sparger'].mass_flowrate)
        print(processes['ctrlPois']['removal_tb_dy'].efficiency)"""
        gc.collect()
        return processes


def read_feeds_from_input():
    feeds = OrderedDict()
    with open(spc_inp_file) as f:
        j = json.load(f)
        # print(j['feeds'])
        for mat, val in j.items():
            feeds[mat] = OrderedDict()
            for obj_name, obj_data in j[mat]['feeds'].items():
                # print(obj_data)
                nucvec = obj_data['comp']
                feeds[mat][obj_name] = Materialflow(nucvec)
                feeds[mat][obj_name].mass = obj_data['mass']
                feeds[mat][obj_name].density = obj_data['density']
                feeds[mat][obj_name].vol = obj_data['volume']
        # print(feeds['fuel']['leu'])
        # print(feeds['ctrlPois']['pure_gd'])
        # print(feeds['fuel']['leu'].print_attr())
        return feeds


# @profile
def reprocessing(mat):
    """ Applies reprocessing scheme to selected material

    Parameters:
    -----------
    mat: Materialflow object`
        Material data right after irradiation in the core/vesel
    Returns:
    --------
    out: Materialflow object
        Material data after performing all removals
    waste: dictionary
        key: process name
        value: Materialflow object containing waste streams data
    """
    inmass = {}
    extracted_mass = {}
    waste = OrderedDict()
    # out = OrderedDict()
    prcs = read_processes_from_input()
    for mname in prcs.keys():  # iterate over materials
        waste[mname] = {}
        extracted_mass[mname] = {}
        inmass[mname] = float(mat[mname].mass)
        print("Material mass before reprocessing %f g" % inmass[mname])
        if mname == 'fuel':
            p = ['sparger',
                 'entrainment_separator',
                 'nickel_filter',
                 'liquid_me_extraction',
                 'heat_exchanger']
            w = ['waste_' + s for s in p]  # modify reprocessing nodes names
            # 1 via Sparger
            waste[mname][w[0]] = prcs[mname][p[0]].rem_elements(mat[mname])
            # 2 via entrainment_entrainment
            waste[mname][w[1]] = prcs[mname][p[1]].rem_elements(mat[mname])
            # 3 via nickel_filter
            waste[mname][w[2]] = prcs[mname][p[2]].rem_elements(mat[mname])
            # Split to two paralell flows A and B
            # A, 10% of mass flowrate
            inflowA = 0.1*mat[mname]
            # 4 via liquid metal process
            waste[mname][w[3]] = prcs[mname][p[3]].rem_elements(inflowA)
            # C. rest of mass flow 90%
            outflowC = 0.9*mat[mname]
            # Feed here
            # Merge out flows 5 via heat exchanger
            mat[mname] = inflowA + outflowC
            waste[mname][w[4]] = prcs[mname][p[4]].rem_elements(mat[mname])
            print('\nMass balance %f g = %f + %f + %f + %f + %f + %f' %
                  (inmass[mname],
                   mat[mname].mass,
                   waste[mname][w[0]].mass,
                   waste[mname][w[1]].mass,
                   waste[mname][w[2]].mass,
                   waste[mname][w[3]].mass,
                   waste[mname][w[4]].mass))
            print('\nMass balance', mat[mname].mass+waste[mname][w[0]].mass+waste[mname][w[1]].mass+waste[mname][w[2]].mass+waste[mname][w[3]].mass+waste[mname][w[4]].mass)
            """print('Volume ', inflowA.vol, inflowB.vol, inflowA.vol+inflowB.vol)
            print('Mass flowrate ', inflowA.mass_flowrate, inflowB.mass_flowrate, out[mname].mass_flowrate)
            print('Burnup ', inflowA.burnup, inflowB.burnup)
            print('\n\n')
            # print('\nInflowA attrs ^^^ \n', inflowA.print_attr())
            # print('\nInflowB attrs ^^^ \n ', inflowB.print_attr())
            print("\nIn ^^^", mat[mname].__class__, mat[mname].print_attr())
            print("\nOut ^^^", out[mname].__class__, out[mname].print_attr())
            # Print data about reprocessing for current step
            print("\nBalance in %f t / out %f t" % (1e-6*inmass[mname], 1e-6*out[mname].mass))"""
            print("Removed FPs %f g" % (inmass[mname]-mat[mname].mass))
            print("Total waste %f g" % (waste[mname][w[0]].mass +
                                        waste[mname][w[1]].mass +
                                        waste[mname][w[2]].mass +
                                        waste[mname][w[3]].mass +
                                        waste[mname][w[4]].mass))
            del inflowA, outflowC
        if mname == 'ctrlPois':
            # print("\n\nPois In ^^^", mat[mname].__class__, mat[mname].print_attr())
            waste[mname]['removal_tb_dy'] = \
                prcs[mname]['removal_tb_dy'].rem_elements(mat[mname])
        extracted_mass[mname] = inmass[mname] - float(mat[mname].mass)
    del prcs, inmass, mname
    return waste, extracted_mass


def refill(mat, extracted_mass, waste_dict):
    """ Applies reprocessing scheme to selected material

    Parameters:
    -----------
    mat: dictionary
        key: Material name
        value: Materialflow object`
        Material data right after reprocessing plant
    extracted_mass: dictionary
        key: Material name
        value: float
        Mass removed as waste in reprocessing function for each material
    Returns:
    --------
    refill_stream: Materialflow object
        Material data after refill
    """
    print('Fuel before refill ^^^', mat['fuel'].print_attr())
    feeds = read_feeds_from_input()
    refill_mat = OrderedDict()
    # out = OrderedDict()
    # print (feeds['fuel'])
    for mn, v in feeds.items():  # iterate over materials
        refill_mat[mn] = {}
        # out[mn] = {}
        for feed_n, fval in feeds[mn].items():  # works with one feed only
            scale = extracted_mass[mn]/feeds[mn][feed_n].mass
            refill_mat[mn] = scale * feeds[mn][feed_n]
            waste_dict[mn]['feed_'+str(feed_n)] = refill_mat[mn]
        mat[mn] += refill_mat[mn]
    print('Refilled fresh fuel %f g' % refill_mat['fuel'].mass)
    print('Refilled fresh Gd %f g' % refill_mat['ctrlPois'].mass)
    print('Refill Material ^^^', refill_mat['fuel'].print_attr())
    print('Fuel after refill ^^^', mat['fuel'].print_attr())
    return waste_dict


def check_restart():
    if not restart_flag:
        try:
            os.remove(db_file)
            os.remove(iter_matfile)
            os.remove(input_file)
        except OSError as e:
            print("Error while deleting file, ", e)


def main():
    """ Inititialize main run
    """
    serpent = Depcode(codename='SERPENT',
                      exec_path=exec_path,
                      template_fname=template_file,
                      input_fname=input_file,
                      output_fname='NONE',
                      iter_matfile=iter_matfile,
                      npop=neutron_pop,
                      active_cycles=active_cycles,
                      inactive_cycles=inactive_cycles)
    simulation = Simulation(sim_name='Super test',
                            sim_depcode=serpent,
                            core_number=cores,
                            node_number=nodes,
                            h5_file=db_file,
                            compression=compression_prop,
                            iter_matfile=iter_matfile,
                            timesteps=steps)

    # Run sequence
    # simulation.runsim_no_reproc()
    # Start sequence
    for dts in range(steps):
        print ("\n\n\nStep #%i has been started" % (dts+1))
        if dts == 0 and restart_flag is False:  # First step
            serpent.write_depcode_input(template_file, input_file)
            serpent.run_depcode(cores, nodes)
            # Read general simulation data which never changes
            simulation.store_run_init_info()
            # Parse and store data for initial state (beginning of dts
            mats = serpent.read_dep_comp(input_file, 0)  # 0)
            simulation.store_mat_data(mats, dts-1, 'before_reproc')
        # Finish of First step
        # Main sequence
        else:
            serpent.run_depcode(cores, nodes)
        mats = serpent.read_dep_comp(input_file, 1)
        simulation.store_mat_data(mats, dts, 'before_reproc')
        simulation.store_run_step_info()
        # Reprocessing here
        print("\nMass and volume of fuel before reproc %f g; %f cm3" %
                                                        (mats['fuel'].mass,
                                                         mats['fuel'].vol))
        print("Mass and volume of ctrlPois before reproc %f g; %f cm3" %
                                                        (mats['ctrlPois'].mass,
                                                         mats['ctrlPois'].vol))
        waste_st, rem_mass = reprocessing(mats)
        print("\nMass and volume of fuel after reproc %f g; %f cm3" %
                                                        (mats['fuel'].mass,
                                                         mats['fuel'].vol))
        print("Mass and volume of ctrlPois after reproc %f g; %f cm3" %
                                                        (mats['ctrlPois'].mass,
                                                         mats['ctrlPois'].vol))
        refill(mats, rem_mass, waste_st)
        print("\nMass and volume of fuel after REFILL %f g; %f cm3" %
                                                        (mats['fuel'].mass,
                                                         mats['fuel'].vol))
        print("Mass and volume of ctrlPois after REFILL %f g; %f cm3" %
                                                        (mats['ctrlPois'].mass,
                                                         mats['ctrlPois'].vol))
        print("Removed mass [g]:", rem_mass)
        # Store in DB after reprocessing and refill (right before next depl)
        simulation.store_after_repr(mats, waste_st, dts)
        serpent.write_mat_file(mats, iter_matfile, dts)
        del mats, waste_st, rem_mass
        gc.collect()


if __name__ == "__main__":
    print('Initiating Saltproc:\n'
          '\tRestart = ' + str(restart_flag) + '\n'
          # '\tNodes = ' + str(nodes) + '\n'
          '\tCores = ' + str(cores) + '\n'
          # '\tSteps = ' + str(steps) + '\n'
          # '\tBlue Waters = ' + str(bw) + '\n'
          '\tSerpent Path = ' + exec_path + '\n'
          '\tTemplate File Path = ' + template_file + '\n'
          '\tInput File Path = ' + input_file + '\n'
          # '\tMaterial File Path = ' + mat_file + '\n'
          # '\tOutput DB File Path = ' + db_file + '\n'
          )
    check_restart()
    main()
    print("\nSimulation succeeded.\n")
