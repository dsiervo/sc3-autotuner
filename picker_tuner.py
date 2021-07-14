# -*- coding: utf-8 -*-
"""
Created on Jun 24 2021
20191201T000000 - 20210101T000000
@author: Daniel Siervo, emetdan@gmail.com
"""
from dataclasses import dataclass
import os
from icecream import ic
ic.configureOutput(prefix='debug| ')


def picker_tuner(cursor, ti, tf, params):
    """Download piciks data (times) and waveforms, performs sta/lta
    via seiscomp playback, performs configuration tuning using
    bayesian optimization

    Parameters
    ----------
    cursor : MySQLdb database cursor
        Cursor to SQL database to perform the picks query
    stations : list
        Stations names list in format: net.sta_code.loc_code.ch, like:
        CM.URMC.00.HH*
    ti : str
        Initial time to search for the picks that will be used in the
        bayesian optimization
    tf : str
        Final time to search for thet picks that will be used in the
        bayesian optimization. Format: yyyy-MM-dd hh:mm:ss
    """

    # Iterating over the list of stations
    station_list = params['stations'].split(',')
    ic(station_list)
    for station_str in station_list:
        # cleaning station_str
        station_str = station_str.strip('\n').strip(' ')
        ic(station_str)
        # creating a station_data object
        sta_data = StationData(cursor, station_str)
        # creating a station object
        station = sta_data.create_station()
        ic(station)
        
        # for each phase
        for phase in ['P', 'S']:
            pass
        # search for picks times and download all waveforms
        
        # Excecutes sta/lta over all wf
        
        # Get pick times from XML files
        
        # Objective function (compare computed times against downloaded times).
        # Return score.
        
        # Optimizer: Use score obtained in previus step to update
        # the picker configuration using bayesian optimization


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
            return self.cursor.fetchall()
        elif self.query_type == 'station_coords':
            return self.cursor.fetchone()
        else:
            raise Exception('query_type does not match with picks or station_coords')


class StationData:
    def __init__(self, cursor, station_str):
        self.cursor = cursor
        self.station_str = station_str
        self.query_dir = os.path.dirname(os.path.realpath(__file__))

    @property
    def coords_query(self):
        query_path = os.path.join(self.query_dir, 'coords_query.sql')
        query_str = open(query_path).read()
        return query_str.format(net=self.net, sta=self.sta, loc=self.loc)
    
    def get_station_codes(self):
        """Creates net, sta, loc, ch"""
        self.net, self.sta, self.loc, self.ch = self.station_str.split('.')
        self.dic_data = {'net': self.net, 'sta': self.sta, 'loc': self.loc}

    def get_station_coords(self):
        query = Query(cursor=self.cursor,
                      query_type='station_coords',
                      dic_data=self.dic_data)
        self.lat, self.lon = query.execute_query()

    def create_station(self):
        self.get_station_codes()
        self.get_station_coords()
        station = Station(float(self.lat), float(self.lon),
                          self.net, self.sta, self.loc, self.ch)
        return station


@dataclass(order=True, frozen=True)
class Station:
    lat: float
    lon: float
    net: str
    name: str
    loc: str
    ch: str


class PicksDownloader:
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

    def __init__(self, cursor, fdsn_client, station: str,
                 radius: int, phase: str, ti: str, tf: str,
                 max_picks: int) -> None:
        """
        Parameters
        ----------
        cursor : MySQLdb database cursor
            Cursor to SQL database to perform the picks query
        fdsn_client : obspy.clients.fdsn.Client
            FDSN client for waveforms downloading
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
