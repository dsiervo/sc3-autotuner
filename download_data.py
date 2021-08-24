from matplotlib.pyplot import phase_spectrum
import numpy as np
import datetime
from dataclasses import dataclass
import obspy
import os
from obspy.clients.fdsn.header import FDSNException
import scipy as sc
import sys

@dataclass
class Station:
    lat: float
    lon: float
    net: str
    name: str
    loc: str
    ch: str


@dataclass
class Waveform:
    t: obspy.UTCDateTime
    wf_id: str
    event_id: str
    ti: obspy.UTCDateTime
    tf: obspy.UTCDateTime


class DirectoryCreator:
    def make_dir(self, dir_root, new_dir_name):
        data_dir = os.path.join(dir_root, new_dir_name)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir


class DownloadWaveform:
    pick: Waveform
    station: Station
    client: obspy.clients.fdsn.Client
    ch: str
    
    def __init__(self, pick, station, client):
        self.pick = pick
        self.station = station
        self.client = client
    
    @property
    def data_dir(self):
        return self.station.data_dir

    @property
    def wf_path(self):
        return os.path.join(self.data_dir,
                            self.wf_name)
    
    @property
    def wf_name(self):
        return self.pick.wf_id+'.mseed'
    
    @property
    def station_dir(self):
        return os.path.split(self.data_dir)[0]

    def get_wf_stream(self):
        try:
            self.st = self.client.get_waveforms(network=self.station.net,
                                                station=self.station.name,
                                                location=self.station.loc,
                                                channel=self.station.ch+'*',
                                                starttime=self.pick.ti,
                                                endtime=self.pick.tf)
            return True
        except FDSNException:
            print('\n\n\tNo se encontraron datos')
            print(f'\t{self.station.net}.{self.station.name}.{self.station.loc}.{self.station.ch}')
            print(f'\t{self.pick.ti} - {self.pick.tf}')
            return False
    
    def trim_and_merge(self):
        self.st.trim(self.pick.ti, self.pick.tf)
        self.st.merge(fill_value="interpolate")
    
    def mseed_check(self):
        # If the mseed file exists do nothing
        if os.path.exists(self.wf_path):
            ic('waveform already exists')
            return False
        else:
            return True

    def write(self):
        self.st.write(self.wf_path)


class PurgeSNR:
    dw: DownloadWaveform
    pick: Waveform
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

        
class PurgeTimes:
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


class CreateWaveform:
    row: list
    station: Station
    dt: int
    
    def __init__(self, row, station, dt):
        self.row = row
        self.station = station
        self.dt = dt

    @property
    def pick_time(self):
        return obspy.UTCDateTime(self.row[-2]
                                 + datetime.timedelta(
                                 milliseconds=float(self.row[-1])/1000))
    
    @property
    def event_id(self):
        return self.row[0]
    
    @property
    def wf_id(self):
        wf_id = f'{self.event_id}.{self.station.name}'
        wf_id += f'.{self.station.loc}.{self.station.ch}'
        wf_id += f'_{self.pick_time.strftime("%Y%m%dT%H%M%S")}'
        return wf_id

    @property
    def ti(self):
        return self.pick_time - self.dt

    @property
    def tf(self):
        return self.pick_time + self.dt

    def create_wf(self):
        return Waveform(self.pick_time, self.wf_id, self.event_id, self.ti, self.tf)


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
        self.main_dir = os.path.dirname(os.path.realpath(__file__))
    
    @property
    def query_path(self):
        return os.path.join(self.main_dir,
                            'utils',
                            'queries',
                            self.query_files[self.query_type])
    
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
            return [list(x) for x in self.cursor.fetchall()]
        elif self.query_type == 'station_coords':
            ch_and_coords = self.cursor.fetchall()
            # list of available channels for this sensor
            channels = [x[0] for x in ch_and_coords]
            lat, lon = ch_and_coords[0][1:]
            return channels, lat, lon
        else:
            raise Exception('query_type does not match with picks or station_coords')




def waveform_downloader(client, station, manual_picks: list, dt: int):

    ic(manual_picks[0])
    # keeping with event id and p times in manual_picks
    p_times = [row[1:5] for row in manual_picks]
    # keeping with event id and s times in manual_picks
    s_times = [list(row[1]) + row[5:8] for row in manual_picks]
    
    # list with p pick objects
    wf_list = [CreateWaveform(pick_row, station, dt).create_wf()
               for pick_row in p_times]

    # purge repeated picks
    purged_wf = PurgeTimes(wf_list).purge()
    ic(len(purged_wf))
    ic(purged_wf[0])

    phase_times = []
    waveforms = {}

    # Download waveforms for each pick
    for waveform in purged_wf:
        download = DownloadWaveform(waveform, station, client)
        
        ic(download.wf_name)
        # checking the mseed file
        mseed_check = download.mseed_check()
        # if the mseed already exists continue to the next waveform
        if not mseed_check:
            continue

        success = download.get_wf_stream()
        # checking if there was no FDSNExeption
        if not success:
            continue
        download.trim_and_merge()
        
        # if the snr is too low and have a lot of peaks continue
        # with the next waveform
        noisy_waveform = PurgeSNR(waveform, download).purge_waveform()
        if noisy_waveform:
            continue
        
        # writing the mseed file
        download.write()
        waveforms[waveform.event_id] = download.wf_name
        

    # write phase times to file
    write_picks(p_times, s_times, waveforms, station)


@dataclass
class PickData:
    row: list
    wf_name: str

    @property
    def time(self):
        return obspy.UTCDateTime(self.row[-2]
                                 + datetime.timedelta(
                                 milliseconds=float(self.row[-1])/1000))

    @property
    def phase_times(self):
        return [self.wf_name, self.time.strftime("%Y-%m-%dT%H:%M:%S.%f")]
    

class WritePhases:
    station: Station
    phase: str
    phase_times: list

    def __init__(self, station, phase, phase_times):
        self.station = station
        self.phase = phase
        self.phase_times = phase_times
    
    @property
    def phases_filename(self):
        name = f'{self.station.name}_{self.phase}_'
        name += f'{self.station.ch}.txt'
        return name

    @property
    def phase_file_path(self):
        return os.path.join(self.station.data_dir,
                            self.phases_filename)
1
    def write(self):
        """Write saved phase times in a csv file on phase_file_path directory"""
        with open(self.phase_file_path, 'w') as f:
            f.write(','.join(self.phase_times))


def write_picks(p_picks, s_picks, waveforms, station):
    picks = {'P': p_picks, 'S': s_picks}
    for phase in picks:
        pick_list = picks[phase]
        ic(pick_list)
        phase_times = []
        for row in pick_list:
            ic(row)
            try:
                wf_name = waveforms[row[0]]
                phase_times.append(PickData(row, wf_name).phase_times)
            except KeyError:
                print(f'{row[0]} not found in waveforms')
                continue
        
        WritePhases(station, phase, phase_times).write
