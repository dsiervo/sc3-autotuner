# -*- coding: utf-8 -*-
"""
Created on Jun 24 2021
20191201T000000 - 20210101T000000
@author: Daniel Siervo, emetdan@gmail.com
"""
from multiprocessing.connection import Client
import sys
import exceptions
import os
import datetime
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNException
import numpy as np
from scipy.signal import find_peaks
from abc import ABC, abstractmethod

from icecream import ic
ic.configureOutput(prefix='debug| ')


def picker_tuner(stations, ti, tf, db_ip, fdsn_ip, max_picks):
    """Download piciks data (times) and waveforms, performs sta/lta
    via seiscomp playback, performs configuration tuning using
    bayesian optimization

    Parameters
    ----------
    stations : list
        Stations names list in format: net.sta_code.loc_code.ch, like:
        CM.URMC.00.HH*
    ti : str
        Initial time to search for the picks that will be used in the
        bayesian optimization
    tf : str
        Final time to search for thet picks that will be used in the
        bayesian optimization. Format: yyyy-MM-dd hh:mm:ss
    db_ip : str
        IP to server with SQL data base for events query
    fdsn_ip : str
        IP to FDSN for waveforms download
    max_picks : int
        Maximun number of picks by station
    """

    for station in stations:
        pass
        # search for picks times and download all waveforms
        
        # Excecutes sta/lta over all wf
        
        # Get pick times from XML files
        
        # Objective function (compare computed times against downloaded times).
        # Return score.
        
        # Optimizer: Use score obtained in previus step to update
        # the picker configuration using bayesian optimization


class Downloader:
    """Search for picks times and download the waveforms

    Atributes
    ---------
    format : str
        Waveform data format

    Methods
    -------
    picks_query()
        Perform sql query to search manual picks
    get_wf()
        Download waveforms according to the sql query result
    """
    format = 'mseed'

    def __init__(self, db_ip: str, station: str, ti: str,
                 tf: str, fdsn_ip: str, max_picks: int) -> None:
        """
        Parameters
        ----------
        db_ip : str
            IP to server with SQL data base for events query
        station : str
            Station name in format: net.sta_code.loc_code.ch, like:
            CM.URMC.00.HH*
        ti : str
            Initial time to search for the picks that will be used in the
            bayesian optimization
        tf : str
            Final time to search for thet picks that will be used in the
            bayesian optimization. Format: yyyy-MM-dd hh:mm:s
        fdsn_ip : str
            IP to FDSN for waveforms download
        max_picks : int
            Maximun number of picks by station
        """
        self.db_ip = db_ip
        self.station = station
        self.ti = ti
        self.tf = tf
        self.fdsn_ip = fdsn_ip
        self.max_picks = max_picks
    
    def picks_query(self):
        """Perform SQL query looking for manual pick times
        """
        ic(self.station)
        self.net, self.sta, self.loc, self.ch = self.station.split('.')


class Downloader(ABC):
    """Search for picks times and download the waveforms

    Atributes
    ---------
    format : str
        Waveform data format

    Methods
    -------
    query()
        Perform sql query to search manual picks or events
    get_wf()
        Download waveforms according to the sql query result
    """
    format = 'mseed'
    
    @abstractmethod
    def query(self, *args, **kwargs):
        """Perform SQL query looking for manual pick times or events
        """
        pass
    
    @abstractmethod
    def download(self, **kwargs):
        """Download data, in case of picker tuner it download waveforms,
        in case of associator tuner it download xml files with picks
        """
        pass
    

class PickerDownloader(Downloader):
    
    def query(self, **kwargs):
        """Expected arguments: ti, tf, fdsn_ip, max_picks, ph,
        station, net, sta_lat, sta_lon
        """
        # updating atributes of the class
        ic(kwargs)
        self.__dict__.update(kwargs)
    
        sta_lat, sta_lon = self.query_station_coordinates()

        sql_query = """
Select distinct 
round(( 6371 * acos(cos(radians({sta_lat})) * cos(radians(Origin.latitude_value)) * cos(radians(Origin.longitude_value) - radians({sta_lon})) + sin(radians({sta_lat})) * sin(radians(Origin.latitude_value)))),2) as radius,
Pick.waveformID_networkCode, Pick.waveformID_locationCode, Pick.waveformID_channelCode, POEv.publicID,
Pick.waveformID_stationCode,
Pick.phaseHint_code,Pick.phaseHint_used,Pick.evaluationMode,Pick.time_value, Pick.time_value_ms
from Event AS EvMF left join PublicObject AS POEv ON EvMF._oid = POEv._oid 
left join PublicObject as POOri ON EvMF.preferredOriginID=POOri.publicID 
left join Origin ON POOri._oid=Origin._oid left join PublicObject as POMag on EvMF.preferredMagnitudeID=POMag.publicID 
left join Magnitude ON Magnitude._oid = POMag._oid 
left join Arrival on Arrival._parent_oid=Origin._oid 
left join PublicObject as POOri1 on POOri1.publicID = Arrival.pickID 
left join Pick on Pick._oid= POOri1._oid 
where 
Magnitude.magnitude_value between 1.2 and 3.0 
AND Pick.phaseHint_used = 1 
AND Pick.evaluationMode = 'manual' 
AND Arrival.phase_code = '{ph}' 
AND Pick.waveformID_stationCode = '{sta}' 
AND Pick.waveformID_networkCode = '{net}' 
AND Magnitude.magnitude_value IS not NULL 
AND Origin.quality_usedPhaseCount IS not null 
AND (EvMF.type NOT IN ('not locatable', 'explosion', 'not existing', 'outside of network interest') OR EvMF.type IS NULL) 
AND Origin.time_value between '{ti}' and '{tf}'
HAVING radius < {radius}
        """.format(sta_lat=sta_lat, sta_lon=sta_lon,
                   ph=self.ph, sta=self.sta,
                   net=self.net, ti=self.ti,
                   tf=self.tf, radius=self.radius)

        # excecuting query
        ic(sql_query)
        self.cursor.execute(sql_query)
        # creating a list for each row without the radious
        self.manual_picks = [list(x).pop(0) for x in self.cursor.fetchall()]
    
    def download(self, **kwargs):
        """Download waveforms using the pick times from the sql query

        Parameters
        ----------
        dt : int
            Delta time in seconds applied to pick time befor and after
            for the download window time
        loc : str
            Station location code
        ch : str
            Station channel
        """
        # updating atributes of the class
        ic(kwargs)
        self.__dict__.update(kwargs)
        
        ic(len(self.manual_picks))

        # Creating a list with valid channles
        self.valid_channels = [stream+ch for stream in ['HH', 'EH', 'HN']
                            for ch in ['Z', 'N', 'E', '*']]
            
        # creating data directory
        main_data_dir = self.dir_creation(self.cwd, 'mseed_data')
        
        # station data dir
        sta_data_dir = self.dir_creation(main_data_dir, self.sta)
            
        # creating phase directory
        self.phase_data_dir = self.dir_creation(sta_data_dir, self.ph)
            
        purge_count = 0
        
        # for each row (for each manual pick)
        for i in range(len(self.manual_picks)):
            
            self.row = self.manual_picks[i]
            
            # don't take into account waveforms time windows
            # where is more than one manual pick
            purge_before, purge_after = self.purge_duplicates(i)
            if purge_before or purge_after:
                purge_count += 1
                continue

            assert self.ch in self.valid_channels, \
                   f'\n The channel "{self.ch}" is not a valid channel,\
                       must be one of the following: {valid_channels}\n'
            if self.ch.endswith('*'):
                
                for ch in ['Z', 'N', 'E']:
                    self.channel = self.ch[:-1] + ch
                    # getting waveform path
                    wf_path = self.get_wf_path()
                    # if the waveform already exists continue with the next pick
                    if os.path.exists(wf_path):
                        break
            
            # donwload waveform, initiallize self.ti and self.df
            self.st = self.download_single()
            # If doesn't find waveform continue with the next pick
            if self.st is None:
                purge_count += 1
                continue

            # purge nosy waveforms, if finds  a noisy waveforms continue
            if self.purge_snr():
                continue
            
            # write each channel of the waveform to a mseed file and write
            # a file with the list of waveforms for each channel
            for tr in self.st():
                # List of paths for each waveform file
                self.ph_times = []
                self.write_channel(tr)
    
    def dir_creation(self, dir_root, new_dir_name):
        data_dir = os.path.join(dir_root, new_dir_name)
        ic(data_dir)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir
        
    def download_single(self):
        try:
            st = self.client.get_waveforms(network=self.net,
                                           station=self.sta,
                                           location=self.loc,
                                           channel=self.ch,
                                           starttime=self.t - self.dt,
                                           endtime=self.t + self.dt)
            st.trim(self.t-self.dt, self.t+self.dt)
            st.merge(fill_value="interpolate")
            tr = self.st[0]
            self.t_i = tr.stats.starttime
            self.df = tr.stats.sampling_rate
            
            return st
        except FDSNException:
            print("\n ############################################")
            print(self.net, self.sta, self.loc, self.ch,
                  self.t-self.dt, self.t+self.dt)
            print('No se encontraron datos!\n')
            return None

    def purge_duplicates(self, i):
        # getting the phase time
        self.t = UTCDateTime(
                self.row[-2]
                + datetime.timedelta(milliseconds=float(self.row[-1])/1000)
                        )

        # checking the current pick is not contained in the previous
        # and consecutive time interval
        purge_before = False
        purge_after = False
        if i == 0:
            purge_after = self.purge_wf(self.manual_picks[i+1])
        elif i == len(self.manual_picks)-1:
            purge_before = self.purge_wf(self.manual_picks[i-1])
        else:
            purge_before = self.purge_wf(self.manual_picks[i-1])
            purge_after = self.purge_wf(self.manual_picks[i+1])
        return purge_before, purge_after

    def purge_wf(self, row):
        """Verify if in row there is another picked phase

        Parameters
        ----------
        row : list
            Checked pick row
        ti : UTCDateTime
            Initial time for the current waveform time interval
        tf : UTCDateTime
            Final time for the current waveform time interval

        Returns
        -------
        bool
            True if the current pick is in the checked row, False otherwise
        """
        
        ti = self.t - self.dt
        tf = self.t + self.dt

        t = UTCDateTime(row[-2]
                        + datetime.timedelta(
                            milliseconds=float(row[-1])/1000
                            ))
        return t < tf and t > ti

    def purge_snr(self):
        """Verify quality of signal"""
        
        # finding data points in waveform to compare signal to noise
        npi, npf = self.phase_point()
        
        st_ = self.st.copy()
        st_.detrend('demean')
        st_.taper(max_percentage=0.05, max_length=30, type="cosine")
        st_.filter("bandpass", freqmin=2.9, freqmax=10.2, corners=4)

        tr2 = st_.copy()[0]
        tr2.normalize()
        data = tr2.data

        snr = np.mean(abs(data[npf:npf+1000]))/np.mean(abs(data[npi-1000:npi]))
        peaks, dic = find_peaks(data, height=0.6)
        #print('\nSNR:', snr, ' peaks:', len(peaks))

        if snr < 1.5 and len(peaks) > 9:
            #print(snr, len(peaks))
            #tr2.plot()
            return True
        else:
            return False

    def phase_point(self):
        """Calcula los extremos de un intervalo de puntos del tiempo ingresado""" 
        
        unc = 1  # 1 second of signal
        t_r_p_i = self.t - self.ti - unc
        t_r_p_f = self.t - self.ti + unc
        n_p_i = int(t_r_p_i * self.df)
        n_p_f = int(t_r_p_f * self.df)
        
        return n_p_i, n_p_f

    def query_station_coordinates(self):
        """Query for the station coordinates of the current station
        """
        pass
    
    def get_wf_path(self):
        self.wf_name = self.row[5]+"_"+self.row[3]+"_"+self.t.strftime("%Y%m%d-%H%M%S")+"_"+self.channel+".mseed"
        return os.path.join(self.phase_data_dir, self.wf_name)
    
    def write_channel(self):
        """Write a mseed file for each pick, and creates a list
        with the paths of them.

        Parameters
        ----------
        tr : obspy.core.trace.Trace
            Trace corresponding to a channel from a pick waveform
        """
        
        self.ph_times.append([name, self.t.strftime("%Y-%m-%dT%H:%M:%S.%f")])
        
            
        # writting waveform on a mseed file
        mseed_path = os.path.join(channel_dir, name)
        tr.write()