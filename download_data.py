import numpy as np
import csv
import datetime
from dataclasses import dataclass
import obspy
import os
from obspy.clients.fdsn.header import FDSNException
import scipy as sc


@dataclass(order=True, frozen=True)
class Station:
    lat: float
    lon: float
    net: str
    name: str
    loc: str
    ch: str


@dataclass
class Pick:
    t: obspy.UTCDateTime
    pick_id: str
    phase: str
    ti: obspy.UTCDateTime
    tf: obspy.UTCDateTime


class DirectoryCreator:
    def make_dir(self, dir_root, new_dir_name):
        data_dir = os.path.join(dir_root, new_dir_name)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir


class DownloadWaveform:
    pick: Pick
    station: Station
    data_dir: str
    client: obspy.clients.fdsn.Client
    ch: str
    
    phase_times = []
    
    def __init__(self, pick, station, data_dir, client, ch):
        self.pick = pick
        self.station = station
        self.data_dir = data_dir
        self.client = client
        self.ch = ch
    
    @property
    def wf_path(self):
        return os.path.join(self.data_dir,
                            self.wf_name)
    
    @property
    def wf_name(self):
        return self.pick.pick_id+f'_{self.ch}'+'.mseed'
    
    @property
    def station_dir(self):
        return os.path.split(self.data_dir)[0]

    @property
    def phases_filename(self):
        name = f'{self.station.name}_{self.pick.phase}_'
        name += f'{self.ch}.txt'
        return name

    def get_wf_stream(self):
        try:
            return self.client.get_waveforms(network=self.station.net,
                                             station=self.station.name,
                                             location=self.station.loc,
                                             channel=self.station.ch+'*',
                                             starttime=self.pick.ti,
                                             endtime=self.pick.tf)
        except FDSNException:
            print('\n\n\tNo se encontraron datos')
            print(f'\t{self.station.net}.{self.station.name}.{self.station.loc}.{self.station.ch}')
            print(f'\t{self.pick.ti} - {self.pick.tf}')
            return None
    
    def trim_and_merge(self):
        self.st.trim(self.pick.ti, self.pick.tf)
        self.st.merge(fill_value="interpolate")
    
    def write_traces(self):
        for tr in self.st:
            tr.write(self.wf_path)
            # saving phase times in a list of list
            self.phase_times.append([self.wf_name,
                                     self.pick.t.strftime("%Y-%m-%dT%H:%M:%S.%f")])
    
    def write_phase_times(self):
        """Write saved phase times in a csv file on station_data_dir directory"""
        with open(os.path.join(self.station_dir, self.phases_filename), 'w') as f:
            writer = csv.writer(f)
            writer.writerows(self.phase_times)
        
    def download(self):
        # If the mseed file exists do nothing
        if os.path.exists(self.wf_path):
            ic('waveform already exists')
            return False
        else:
            self.st = self.get_wf_stream()
            # If there is not FDSN exception
            if self.st is not None:
                self.trim_and_merge()
                self.write_traces()
                return True
            else:
                return False


class PurgeSNR:
    dw: DownloadWaveform
    pick: Pick
    unc: int = 1
    
    def __init__(self, pick, dw):
        self.dw = dw
        self.pick = pick
    
    @property
    def t(self):
        return self.dw.pick.t
    
    @property
    def ti(self):
        return self.dw.pick.ti
    
    @property
    def tf(self):
        return self.dw.pick.tf
    
    @property
    def sampling_rate(self):
        return self.dw.st[0].stats.sampling_rate
    
    def phase_point(self):
        """Compute the data points for an enter interval"""
        tr_i = self.t - self.ti - self.unc
        tr_f = self.t - self.tf + self.unc
        
        npi = int(tr_i * self.sampling_rate)
        npf = int(tr_f * self.sampling_rate)
        return npi, npf

    def purge_waveform(self):
        """verify quality of the waveform base on signal noise ratio
        and number of peaks"""
        st_ = self.dw.st.copy()
        # detrend and remove mean
        st_.detrend('demean')
        # apply taper and filter
        st_.taper(max_percentage=0.05, max_length=30, type='cosine')
        st_.filter('bandpass', freqmin=2.9, freqmax=10.2, corners=4)
        
        tr = st_.copy()[0]
        tr.normalize()
        
        npi, npf = self.phase_point()
        
        signal = tr.data[npf:npf+1000]
        noise = tr.data[npi-1000:npi]
        
        snr = np.mean(abs(signal)) / np.mean(abs(noise))
        peaks, _ = sc.signal.find_peaks(tr.data, height=0.6)
        ic(snr, len(peaks),  snr < 1.5 and len(peaks) > 9)
        
        # if the signal is too noisy, and have many peaks,
        # do not keep the waveform
        if snr < 1.5 and len(peaks) > 9:
            return True
        else:
            return False

        
class PurgePicks:
    pick_list: list
    
    def __init__(self, pick_list):
        self.pick_list = pick_list
        self.purge_before = False
        self.purge_after = False
    
    def purge(self):
        purged_pick_list = []
        for i, pick in enumerate(self.pick_list):
            pick
            # if is the first pick
            if i == 0:
                self.purge_after = self.compare_times(pick, self.pick_list[1])
            # if is the last pick
            elif i == len(self.pick_list)-1:
                self.purge_before = self.compare_times(pick, self.pick_list[i-1])
            else:
                self.purge_after = self.compare_times(pick, self.pick_list[1])
                self.purge_before = self.compare_times(pick, self.pick_list[i-1])

            if self.purge_before or self.purge_after:
                pass
            else:
                purged_pick_list.append(pick)

        return purged_pick_list

    def compare_times(self, pick, pick2):
        return pick.ti < pick2.t < pick.tf


class CreatePick:
    row: list
    station: Station
    phase: str
    dt: int
    
    def __init__(self, row, station, phase, dt):
        self.row = row
        self.station = station
        self.phase = phase
        self.dt = dt

    @property
    def pick_time(self):
        return obspy.UTCDateTime(self.row[-2]
                                 + datetime.timedelta(
                                 milliseconds=float(self.row[-1])/1000))
    
    @property
    def pick_id(self):
        return f'{self.phase}__{self.row[0]}-{self.station.name}.{self.station.loc}.{self.station.ch}__{self.row[1]}-{self.row[2]}'

    @property
    def ti(self):
        return self.pick_time - self.dt

    @property
    def tf(self):
        return self.pick_time + self.dt

    def create_pick(self):
        return Pick(self.pick_time, self.pick_id, self.phase, self.ti, self.tf)


class Query:
    """General class for perfom queries to sql seiscomp3 db
    
    Atributes
    ---------
    query_files : dict
        Filenames for the slq script to search for pick times or
        to search for station data.
    """
    query_files = {'picks': 'picks_query.sql',
                   'station_coords': 'coords_query.sql'}
    
    def __init__(self, cursor, query_type: str, dic_data: dict):
        """General class for perfom sql queries

        Parameters
        ----------
        cursor : MySQLdb.connect.cursor
            Cursor pointed to seiscomp3 database
        query_type : str
            Could be picks or station
        dic_data : dict
            Dictionary with the data to complete the query
        """
        self.cursor = cursor
        self.query_type = query_type
        self.dic_data = dic_data
        self.query_dir = os.path.dirname(os.path.realpath(__file__))
    
    @property
    def query_path(self):
        return os.path.join(self.query_dir, self.query_files[self.query_type])
    
    @property
    def query_str(self):
        return open(self.query_path).read()
    
    @property
    def query(self):
        return self.query_str.format(**self.dic_data)
    
    def execute_query(self):
        self.cursor.execute(self.query)
        if self.query_type == 'picks':
            # pop(0) deletes the radius column
            return [list(x)[1:] for x in self.cursor.fetchall()]
        elif self.query_type == 'station_coords':
            ch_and_coords = self.cursor.fetchall()
            # list of available channels for this sensor
            channels = [x[0] for x in ch_and_coords]
            lat, lon = ch_and_coords[0][1:]
            return channels, lat, lon
        else:
            raise Exception('query_type does not match with picks or station_coords')