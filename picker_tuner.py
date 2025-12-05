# -*- coding: utf-8 -*-
"""
Created on Jun 24 2021
20191201T000000 - 20210101T000000
@author: Daniel Siervo, emetdan@gmail.com
"""

import os
import sys
from download_data import Query, Station, waveform_downloader, DirectoryCreator
import obspy
from MySQLdb import OperationalError
from optimizer import bayes_optuna
from icecream import ic, install
ic.configureOutput(prefix='debug| ')  # , includeContext=True)
install()


def picker_tuner(cursor, wf_cursor, ti, tf, params):
    """Download piciks data (times) and waveforms, performs sta/lta
    via seiscomp playback, performs configuration tuning using
    bayesian optimization

    Parameters
    ----------
    cursor : MySQLdb database cursor
        Cursor to SQL database to perform the picks query
    wf_cursor : MySQLdb database cursor
        Cursor to SQL database to perform the waveform query
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
    
    # time in seconds after and before pick for waveform extraction
    DT = 100
    
    # current working directory (directory from where the program is running)
    CWD = os.getcwd()

    try:
        # defining radius in km for picks search
        radius = float(params['radius'])
    except KeyError:
        print('\033[91m\n\n\n\n\t', end='')
        print(f"You did not define a radius (km) parameter in the sc3-autuner.inp file")
        print(f"\tAsuming 100")
        print('\033[0m', end='\n\n\n')
        radius = 100
    except ValueError:
        print('\033[91m\n\n\n\n\t', end='')
        print(f"Wrong radius value given")
        print(f"\tAsuming 100")
        print('\033[0m', end='\n\n\n')
        radius = 100       

    try:
        # defining minimum magnitude for picks search
        min_mag = float(params['min_mag'])
    except KeyError:
        print('\033[91m\n\n\n\n\t', end='')
        print(f"You did not define a min_mag parameter in the sc3-autuner.inp file")
        print(f"\tAsuming 1.2")
        print('\033[0m', end='\n\n\n')
        min_mag = 1.2
    except ValueError:
        print('\033[91m\n\n\n\n\t', end='')
        print(f"Wrong min_mag value given")
        print(f"\tAsuming 1.2")
        print('\033[0m', end='\n\n\n')
        min_mag = 1.2

    # seiscomp3 inventory in xml format
    inv_xml = params['inv_xml']
    # check if inv_xml file exists
    if not os.path.isfile(inv_xml):
        # print in red color error message
        print('\033[91m\n\n\t', end='')
        print(f'Error: inv_xml file: {inv_xml} does not exist')
        print('\033[0m', end='\n')
        sys.exit()
    
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
        #client = obspy.clients.fdsn.Client(params['fdsn_ip'])
        clients = [obspy.clients.fdsn.Client(ip.strip()) for ip in params['fdsn_ip'].split(',')]
        ic(clients)
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

        if not wf_cursor:
            wf_cursor = cursor
        # searching for station coordinates
        query_coords = Query(cursor=wf_cursor,
                             query_type='station_coords',
                             dic_data={'net': net,
                                       'sta': sta,
                                       'loc': loc,
                                       'ch': ch_})

        try:                               
            channels, lat, lon = query_coords.execute_query()
        except OperationalError:
            print('\033[91m\n\n\n\n\t', end='')
            print(f"Lost connection to MySQL server during coords query, station {sta}")
            print(f"\tContinuing with the next one...")
            print('\033[0m', end='\n\n\n')
            # writing in a file that the station could not be tuned
            not_tuned_station(sta+' lost connection to MySQL during coords query')
            continue            
        # if the sql query dont find data about the station continue with the
        # next one
        if (channels, lat, lon) == (0,0,0):
            print('\033[91m\n\n\n\n\t', end='')
            print(f"Unable to find information about the station {sta}")
            print(f"\tContinuing with the next one...")
            print('\033[0m', end='\n\n\n')
            # writing in a file that the station could not be tuned
            not_tuned_station(sta+' station not found in the SQL DB')
            continue

        ic(channels)
        # creating a station object
        station = Station(lat, lon, net, sta, loc, ch_)
        ic(station)
        # creating station directory
        station.data_dir = dir_maker.make_dir(main_data_dir, sta)
        
        print(f'\n\n\033[95m {net}.{sta}.{ch_} |\033[0m Searching for manual picks between {ti} and {tf}\n')
        # search for manual picks times
        query_picks = Query(cursor=cursor,
                            query_type='picks',
                            dic_data={'sta': sta, 'net': net,
                                      'sta_lat': lat, 'sta_lon': lon,
                                      'ti': ti, 'tf': tf,
                                      'min_mag': min_mag,
                                      'radius': radius,
                                      'max_picks': MAX_PICKS})
        manual_picks = query_picks.execute_query()
        if len(manual_picks) < 5:
            print(f'Less than 5 manual picks found ({len(manual_picks)}) for {station.name}')
            not_tuned_station(station.name+' less than 5 picks found')
            continue           
        print(f'\n\n\033[95m {net}.{sta}.{ch_} |\033[0m Found {len(manual_picks)} manual picks between {ti} and {tf}\n')
        # store manual picks in csv file
        picks_file = os.path.join(station.data_dir, f'{station.name}_manual_picks.csv')
        print(f'\n\n\033[95m {net}.{sta}.{ch_} |\033[0m Downloading waveforms\n')
        times_paths = waveform_downloader(clients, station, manual_picks, DT)

        # if the program couldn't download any waveform for the current station
        # continue with the following one
        if times_paths is None:
            print(f'No waveforms downloaded for {station.name} due lack of good picks')
            not_tuned_station(station.name+' lack good picks')
            continue
        # Excecutes sta/lta over all wf
        # creating xml picks directory
        picks_dir = dir_maker.make_dir(CWD, 'picks_xml')
        image_dir = dir_maker.make_dir(CWD, 'images')
        
        print(f'\n\n\033[95m {net}.{sta}.{ch_} |\033[0m Optimizing pickers\n')
        for phase in ['P', 'S']:
            write_current_exc(times_paths[phase], picks_dir, inv_xml, debug,
                              net, ch_, loc, sta)
            ic(phase)
            bayes_optuna(net, sta, loc, ch_, phase, n_trials)

def not_tuned_station(station):
    with open('stations_not_tuned.txt', 'a') as f:
        f.write(f'{station}\n')
    

def write_current_exc(times_paths, picks_dir, inv_xml, debug,
                      net, ch, loc, sta):
    """function that writes in a file called current_exc.txt
    the values of times_paths, picks_dir, inv_xml, and debug
    times_file: str
    picks_dir: str
    inv_xml: str
    debug: bool
    """
    f = open('current_exc.txt', 'w')
    f.write(f"times_file = {times_paths}\n")
    f.write(f"picks_dir = {picks_dir}\n")
    f.write(f"inv_xml = {inv_xml}\n")
    f.write(f"_debug = {debug}\n")
    f.write(f"net = {net}\n")
    f.write(f"ch = {ch}\n")
    f.write(f"loc = {loc}\n")
    f.write(f"sta = {sta}\n")
    f.close()

