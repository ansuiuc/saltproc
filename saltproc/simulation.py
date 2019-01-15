import h5py
from silx.io.dictdump import dicttoh5


class Simulation():
    """ Class setups parameters for simulation, runs SERPENT, parse output,
    create input.
    """

    def __init__(
            self,
            sim_name,
            sim_depcode,
            core_number,
            db_file):
        """ Initializes the class

        Parameters:
        -----------
        sim_name: string
            name of simulation may contain number of reference case, paper name
             or other specific information to identify simulation
        cores: int
            number of cores to use for SERPENT run
        nodes: int
            number of nodes to use for SERPENT run
        bw: string
            # !! if 'True', runs saltproc on Blue Waters
        sss_exec_path: string
            path to SERPENT executable
        restart: bool
            if 'True', restarts simulation using existing HDF5  database
        timestep: int
            duration of each depletion simulation
        t_0: int
            beggining of simulation moment in time (0 for new run, >0 when
             restarting)
        t_final: int
            duration of whole Saltproc simulation
        input_filename: string
            name of JSON input file with reprocessing scheme and parameters for
             Saltproc simulation
        db_file: string
            name of HDF5 database
        connection_graph: dict
            key: ???
            value: ???
        """
        # initialize all object attributes
        self.sim_name = sim_name
        self.sim_depcode = sim_depcode
        self.core_number = core_number
        self.db_file = db_file

    def runsim(self):
        # self.sim_depcode.write_depcode_input(self.sim_depcode.template_fname,
        #                                      self.sim_depcode.input_fname)
        # self.sim_depcode.run_depcode(self.core_number)
        self.sim_depcode.read_bumat(self.sim_depcode.input_fname,
                                    1)
        # self.sim_depcode.read_bumat(self.sim_depcode.input_fname,
        #                             1)
        # self.init_db()

    def steptime(self):
        return

    def loadinput_sp(self):
        return

    def init_db(self):
        """ Initializes the database  """
        dicttoh5(self.sim_depcode.depl_dict, self.db_file,
                 create_dataset_args={'compression': "gzip",
                                      'shuffle': True,
                                      'fletcher32': True,
                                      'dtype': 'f8'})

    def reopen_db(self):
        return

    def write_db(self):
        return
