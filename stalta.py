# -*- coding: utf-8 -*-
"""
Classes and functions to compute sta/lta in seiscomp3

Created on Jul 20 2021
@author: Daniel Siervo, emetdan@gmail.com
"""
#from obspy import read, UTCDateTime
import obspy
import os
import xml.etree.ElementTree as ET
import pandas as pd
from obspy.core import UTCDateTime
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from icecream import ic
from config_params import DEFAULT_VALUES, render_config_param_templates

ic.configureOutput(prefix='debug| ')  # , includeContext=True)


class StaLta:
    times_file: str
    picks_dir: str
    inv_xml: str
    _debug: bool
    best_p_csv = 'results_P.csv'
    
    main_dir: str = os.path.dirname(os.path.realpath(__file__))
    
    def __init__(self):
        self.__dict__.update(self._current_exc_params)
    
    @property
    def best_p_params(self):
        """
        Get the best p parameters
        """
        df = pd.read_csv(self.best_p_csv)
        # selecting the row with net.sta equal to CM.BAR2 and with the highest value of best_f1
        p_best = df[df['net.sta'] == f'{self.net}.{self.sta}'].sort_values(by='best_f1', ascending=False).iloc[0].to_dict()
        return p_best
    
    @property
    def _current_exc_params(self):
        """function that reads from a file called current_exc.txt
        the values of times_paths['P'] or times_paths['S'], picks_dir, inv_xml, and debug
        """
        f = open('current_exc.txt', 'r')
        lines = f.readlines()
        f.close()
        dic = {}
        for line in lines:
            line = line.strip('\n').strip(' ')
            key, value = line.split('=')
            dic[key.strip()] = value.strip()
        return dic

    @property
    def debug(self):
        return True if self._debug in ['true', 'True', 'TRUE'] else False

    @property
    def times_file_name(self):
        return os.path.basename(self.times_file)

    @property
    def station_name(self):
        return self.times_file_name.split('_')[0]

    @property
    def phase(self):
        return ic(self.times_file_name.split('_')[-2])
    
    @property
    def lines(self):
        return open(self.times_file, 'r').readlines()
    
    @property
    def N(self):
        return len(self.lines)
    
    @property
    def max_workers(self):
        """
        Get the maximum number of workers if debug is false
        """
        if self.debug:
            return 1
        else:
            return int(os.cpu_count() * 1)

    def mega_sta_lta(self, config_db_path=None, **kwargs):
        """
        Compute sta/lta for all lines in the file
        """
        kwargs.update(self._current_exc_params)
        self.remove_picks_dir()
        if config_db_path is None:
            self.edit_xml_config(**kwargs)
        else:
            self.xml_exc_path = config_db_path
        
        Y_obs_ = []
        Y_pred_ = []
        """for line in self.lines:
            self.exc_read_transform(line)
            Y_obs_.append(self.y_obs)
            Y_pred_.append(self.y_pred)
        
        Y_obs = np.concatenate(Y_obs_)
        Y_pred = np.concatenate(Y_pred_)"""
        
        # self.max_workers
        # execute scautopick in parallel and saving the results in Y_obs and Y_pred
        with ProcessPoolExecutor(max_workers=self.max_workers) as excecutor:
            for y_obs, y_pred in excecutor.map(self.exc_read_transform, self.lines):
                Y_obs_.append(y_obs)
                Y_pred_.append(y_pred)

        Y_obs = np.concatenate(Y_obs_)
        Y_pred = np.concatenate(Y_pred_)
                                
        ic(Y_obs)
        ic(Y_pred)
        ic(np.unique(Y_obs))
        ic(np.unique(Y_pred))
        # plot if debug is true
        if self.debug:
            print('\n\nFinishing mega_sta_lta')
            print('Running test_binary_times...\n')
            self.test_binary_times(Y_obs, Y_pred)
        return Y_obs, Y_pred

    def exc_read_transform(self, line):
        self.sta_lta_compute(line)
        try:
            # get pick times
            self.pick_times = XMLPicks(self.pick_path, self.phase).get_pick_times()
            # print(f'self.pick_path: {self.pick_path}')
            # print(f'self.pick_times: {self.pick_times}')
            # print(f'self.phase: {self.phase}')
        except TypeError:
            ic()
            # if no pick is found, set pick times to empty list
            self.pick_times = []
        except KeyError:
            ic()
            self.pick_times = []
            
        # transform predicted times into a binary time series
        y_pred = BinaryTransform(self.wf_start_time,
                                      self.sample_rate,
                                      self.npts,
                                      self.pick_times).transform()
        y_obs = BinaryTransform(self.wf_start_time,
                                     self.sample_rate,
                                     self.npts,
                                     self.ph_time).transform()
        if self.debug:
            print('\n\nFinishing exc_read_transform')
            print('Running test_binary_time...\n')
            self.test_binary_time(y_pred)
        
        return y_obs, y_pred

    def time2sample(self, time: UTCDateTime):
        """
        Convert a time into a sample
        """
        return int((time - self.wf_start_time) * self.sample_rate)

    def test_binary_times(self, y_obs, y_pred):
        import matplotlib
        import matplotlib.pyplot as plt
        #matplotlib.use('Agg') 

        plt.figure()
        plt.plot(y_obs, label='Y_obs')
        plt.plot(y_pred, "--r", label='Y_pred')
        plt.legend()
        plt.show()
        
    def test_binary_time(self, y_pred):
        import obspy as obs
        import matplotlib.pyplot as plt
        print('In test_binary_times')
        
        
        st = obs.read(self.wf_path)
        tr = st[0]
        
        # getting the pick times in counts of samples
        tc = [self.time2sample(t) for t in self.pick_times]
        
        plt.figure(figsize=(8, 4))
        plt.subplot(211)
        plt.plot(tr.data, color='k', lineWidth=0.5)
        plt.vlines(tc, -5000, 5000, color='r', zorder=10)
        plt.legend(['waveform', 'predicted picks'])
        plt.title(f'{self.station_name} {self.phase}')
        plt.xticks([])
        plt.ylabel('Amplitude')
        plt.subplot(212)
        plt.plot(y_pred)
        plt.show()

    def remove_picks_dir(self):
        """
        Remove the picks directory content if it exists
        """
        if os.path.exists(self.picks_dir):
            os.system(f'rm {self.picks_dir}/*')
        
    def sta_lta_compute(self, line: str):
        """
        Compute sta/lta for a single line
        """
        fields = line.split(',')
        pick_value = fields[1].strip("\n\r")
        if pick_value in ['', 'NO_PICK']:
            self.ph_time = []
        else:
            self.ph_time = [obspy.UTCDateTime(pick_value)]
        # get the initial waveform time
        self.wf_start_time = obspy.UTCDateTime(fields[2].strip("\n\r"))
        # get the sample rate
        self.sample_rate = float(fields[3].strip("\n\r"))
        # get the number of samples
        self.npts = int(fields[4].strip("\n\r"))
        self.wf_path = fields[0]
        
        self.run_scautopick()
    
    @property
    def xml_exc_name(self):
        return f'exc_{self.station_name}_{self.phase}.xml'
    
    def edit_xml_config(self, **kwargs):
        """
        Edit the config.xml file
        """
        # Set default values from central configuration
        for key, value in DEFAULT_VALUES.items():
            kwargs.setdefault(key, value)

        if self.phase == 'P':
            xml_filename = 'config_template_P.xml'
            required_keys = ['p_sta', 'p_lta', 'p_fmin', 'p_fmax', 'p_snr', 'trig_on']
        else:
            xml_filename = 'config_template.xml'
            required_keys = ['p_sta', 'p_lta', 'p_fmin', 'p_fmax', 'p_snr', 'trig_on',
                             's_snr', 's_fmin', 's_fmax']

        missing = [key for key in required_keys if key not in kwargs]
        if missing:
            raise KeyError(f"Missing required parameters for {self.phase} configuration: {', '.join(missing)}")

        kwargs['aic_fmax'] = kwargs['aic_fmin'] + kwargs['aic_fwidth']

        # Precompute config parameter strings so templates can consume them
        kwargs.update(render_config_param_templates(kwargs))
    
        ic(xml_filename)
        # xml path for the template
        xml_path = os.path.join(self.main_dir, 'bindings', xml_filename)
        xml_str = open(xml_path, 'r').read()
        
        # xml path for the excecution of scautopick
        self.xml_exc_path = os.path.join(os.getcwd(), self.xml_exc_name)
        # Edit the config.xml file
        with open(self.xml_exc_path, 'w') as f:
            f.write(ic(xml_str.format(**kwargs)))
    
    def run_scautopick(self):
        """
        Run scautopick
        """
        #debug_line = ' --debug' if self.debug else ''
        debug_line = ''
        # Run scautopick
        cmd = f'scautopick -I {self.wf_path} --config-db {self.xml_exc_path}'
        cmd += f' --amplitudes 0 --inventory-db {self.inv_xml}'
        cmd += f' --playback --ep{debug_line}>{self.pick_path}'
        ic(cmd)
        #print(cmd)
        os.system(cmd)

    @property
    def picks_name(self):
        """
        Return the name of the pick file
        """
        return os.path.basename(self.wf_path).split('.')[0] + '_picks.xml'
    
    @property
    def pick_path(self):
        return os.path.join(self.picks_dir, self.picks_name)

class XMLPicks:
    xml_path: str
    ns: dict = {'seiscomp': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.13'}
    
    def __init__(self, xml_path: str, phase: str):
        self.xml_path = xml_path
        self.phase = phase
        self.check_ns_url_match()  # Ensure ns URL matches before proceeding

    def check_ns_url_match(self):
        """
        Check if the namespace URL in the XML file matches the expected URL in the class's ns attribute.
        Raises a ValueError if there is a mismatch.
        """
        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            file_ns_url = root.tag[root.tag.find("{") + 1:root.tag.find("}")]
            
            expected_ns_url = self.ns['seiscomp']
            if file_ns_url != expected_ns_url:
                raise ValueError(
                    f"Namespace URL mismatch: Expected '{expected_ns_url}', but found '{file_ns_url}' "
                    f"in the XML file '{self.xml_path}'. Please check that the schema coincides with the expected URL."
                )
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML file '{self.xml_path}': {str(e)}")

    def open_dict_time(self, x):
        return x['value']

    def get_pick_times(self):
        """
        Return automatic pick times from an XML file.
        """
        times = []
        root = ET.parse(self.xml_path).getroot()
        for pick in root.findall('seiscomp:EventParameters/seiscomp:pick', self.ns):
            if self.phase == pick.find('seiscomp:phaseHint', self.ns).text:
                time = pick.find('seiscomp:time/seiscomp:value', self.ns).text
                ic(time)
                times.append(obspy.UTCDateTime(time))
        return times


    """def get_pick_times(self):
        ic(self.xml_path)

        df = pdx.read_xml(self.xml_path,
                          ['seiscomp', 'EventParameters', 'pick'])

        df['time'] = pd.to_datetime(df['time'].apply(self.open_dict_time))
        
        t = df['time'].dt.tz_localize(None).astype('str').to_list()
        times = [UTCDateTime(i) for i in t]
        return np.array(times)"""


class BinaryTransform:
    """
    Transform pick times into a binary time series
    """
    unc: float = 0.25
    
    def __init__(self, wf_start_time: UTCDateTime, sample_rate: float,
                 npts: int, ph_times: list):
        self.wf_start_time = wf_start_time
        self.ph_times = ph_times
        self.sample_rate = sample_rate
        self.npts = npts
    
    def transform(self):
        """
        Transform pick times into a binary time series
        """
        z = np.zeros(self.npts)
        
        if len(self.ph_times) == 0:
            return z
        
        # transform pick times into a binary time series
        for ph_time in self.ph_times:
            # get the sample points for the phase time +/- uncertainty
            n_ph_i, n_ph_f = self.phase_point(ph_time,
                                              self.wf_start_time,
                                              self.sample_rate,
                                              self.unc)
            
            # fill the time series with 1 between the sample points
            z[n_ph_i:n_ph_f] = 1
        return z
        
    def phase_point(self, t, ti, df, unc):
        """Calcula los extremos de un intervalo de puntos del tiempo ingresado""" 
        t_r_p_i = t-ti-unc
        t_r_p_f = t-ti+unc
        n_p_i = int(t_r_p_i*df)
        n_p_f = int(t_r_p_f*df)
        return n_p_i, n_p_f
