# -*- coding: utf-8 -*-
"""
Created on Jun 24 2021
20191201T000000 - 20210101T000000
@author: Daniel Siervo, emetdan@gmail.com
"""

import os
from download_data import Query, Station, waveform_downloader, DirectoryCreator
import obspy
from icecream import ic, install
ic.configureOutput(prefix='debug| ')  # , includeContext=True)
install()


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

    # defining radius of 2 degrees in km for picks search
    RADIUS = 111*2
    
    # time after and before pick for waveform extraction
    DT = 100
    
    # current working directory (directory from where the program is running)
    CWD = os.getcwd()
    
    # fdsn client for waveforms download
    client = obspy.clients.fdsn.Client(params['fdsn_ip'])
    
    # creating data directory
    dir_maker = DirectoryCreator()
    main_data_dir = dir_maker.make_dir(CWD, 'mseed_data')
    ic(main_data_dir)
    
    # Iterating over the list of stations
    station_list = params['stations'].split(',')
    ic(station_list)
    for station_str in station_list:
        # cleaning station_str and getting station codes
        station_str = station_str.strip('\n').strip(' ')
        ic(station_str)
        net, sta, loc, ch_ = station_str.split('.')
        assert len(ch_) == 2,\
            f"\n\tEl canal {ch_} para la estación {sta} no es válido\n|"

        # searching for station coordinates
        query_coords = Query(cursor=cursor,
                             query_type='station_coords',
                             dic_data={'net': net,
                                       'sta': sta,
                                       'loc': loc,
                                       'ch': ch_})
        channels, lat, lon = query_coords.execute_query()

        # creating a station object
        station = Station(lat, lon, net, sta, loc, ch_)
        ic(station)
        # creating station directory
        station.data_dir = dir_maker.make_dir(main_data_dir, sta)
        
        # search for manual picks times
        query_picks = Query(cursor=cursor,
                            query_type='picks',
                            dic_data={'sta': sta, 'net': net,
                                      'sta_lat': lat, 'sta_lon': lon,
                                      'ti': ti, 'tf': tf,
                                      'radius': RADIUS})
        manual_picks = query_picks.execute_query()

        waveform_downloader(client, station, manual_picks, DT)
            # Excecutes sta/lta over all wf
        
            # Get pick times from XML files
        
            # Objective function (compare computed times against downloaded times).
            # Return score.
        
            # Optimizer: Use score obtained in previus step to update
            # the picker configuration using bayesian optimization


