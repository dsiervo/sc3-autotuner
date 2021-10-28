# -*- coding: utf-8 -*-
"""
Created on Jun 24 2021
20191201T000000 - 20210101T000000
@author: Daniel Siervo, emetdan@gmail.com
"""

import os
import sys
from download_data import Query, Station, Waveform, waveform_downloader, DirectoryCreator
from stalta import StaLta
import obspy
from optimizer import bayes_optuna
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
    
    # seiscomp3 inventory in xml format
    inv_xml = params['inv_xml']
    
    # define if the program is running in debug mode
    debug = params['debug']
    
    try:
        n_trials = int(params['n_trials'])
    except ValueError:
        # printtig warning message in red color, we are using default value of n_trials = 100
        n_trials = 100
        print(f"\033[91m\n\tWARNING: n_trials is not an integer, got {params['n_trials']}. Using default value of n_trials = 100\n\033[0m")
    
    MAX_PICKS = params['max_picks']
    """try:
        MAX_PICKS = params['max_picks']
    except KeyError:
        print('\n\n\t Warning: max_picks not defined in sc3-autotuner.inp assuming 50\n\n')
        MAX_PICKS = 50"""
    
    try:
        # fdsn client for waveforms download
        client = obspy.clients.fdsn.Client(params['fdsn_ip'])
    except KeyError:
        print('\n\n\t ERROR! fdsn_ip not defined in sc3-autotuner.inp')

    # creating data directory
    dir_maker = DirectoryCreator()
    main_data_dir = dir_maker.make_dir(CWD, 'mseed_data')
    ic(main_data_dir)
    
    try:
        # Iterating over the list of stations
        station_list = params['stations'].split(',')
    except KeyError:
        print('\n\n\tERROR! No stations defined in sc3-autotuner.inp\n\n')
        sys.exit()

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
        ic(channels)
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
                                      'radius': RADIUS,
                                      'max_picks': MAX_PICKS})
        manual_picks = query_picks.execute_query()

        times_paths = waveform_downloader(client, station, manual_picks, DT)
        # Excecutes sta/lta over all wf
        # creating xml picks directory
        picks_dir = dir_maker.make_dir(CWD, 'picks_xml')
        image_dir = dir_maker.make_dir(CWD, 'images')
        write_current_exc(times_paths, picks_dir, inv_xml, debug,
                          net, ch_, loc, sta)
        
        # for phase in ['P', 'S']:
        phase = 'P'
        bayes_optuna(net, sta, loc, phase, n_trials)
    
        # Objective function (compare computed times against downloaded times).
        # Return L2 score for all picks.
        
    
        # Optimizer: Use score obtained in previus step to update
        # the picker configuration using bayesian optimization

def write_current_exc(times_paths, picks_dir, inv_xml, debug,
                      net, ch, loc, sta):
    """function that writes in a file called current_exc.txt
    the values of times_paths['P'], picks_dir, inv_xml, and debug
    times_file: str
    picks_dir: str
    inv_xml: str
    debug: bool
    """
    f = open('current_exc.txt', 'w')
    f.write(f"times_file = {times_paths['P']}\n")
    f.write(f"picks_dir = {picks_dir}\n")
    f.write(f"inv_xml = {inv_xml}\n")
    f.write(f"_debug = {debug}\n")
    f.write(f"net = {net}\n")
    f.write(f"ch = {ch}\n")
    f.write(f"loc = {loc}\n")
    f.write(f"sta = {sta}\n")
    f.close()

