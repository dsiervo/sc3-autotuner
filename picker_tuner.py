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
import pandas as pd
from MySQLdb import OperationalError
from optimizer import bayes_optuna
from reference_picker import (
    ComparisonCollector,
    build_reference_scautopick_xml,
    format_comparison_table,
    resolve_reference_station_file,
)
from stalta import StaLta
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
    def parse_float_param(param_name, default_value, missing_message, invalid_message):
        try:
            return float(params[param_name])
        except KeyError:
            print('\033[91m\n\n\n\n\t', end='')
            print(missing_message)
            print(f"\tAsuming {default_value}")
            print('\033[0m', end='\n\n\n')
            return default_value
        except ValueError:
            print('\033[91m\n\n\n\n\t', end='')
            print(invalid_message)
            print(f"\tAsuming {default_value}")
            print('\033[0m', end='\n\n\n')
            return default_value

    # time in seconds after and before pick for waveform extraction
    DT = 100
    
    # current working directory (directory from where the program is running)
    CWD = os.getcwd()

    # defining radius in km for picks search
    radius = parse_float_param(
        'radius',
        100,
        "You did not define a radius (km) parameter in the sc3-autuner.inp file",
        "Wrong radius value given",
    )

    # defining minimum magnitude for picks search
    min_mag = parse_float_param(
        'min_mag',
        1.2,
        "You did not define a min_mag parameter in the sc3-autuner.inp file",
        "Wrong min_mag value given",
    )

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

    download_noise_p = params.get('download_noise_p', False)
    if isinstance(download_noise_p, str):
        download_noise_p = download_noise_p.lower() in ['true', '1', 'yes']
    
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
        sys.exit()

    # creating data directory
    dir_maker = DirectoryCreator()
    main_data_dir = dir_maker.make_dir(CWD, 'mseed_data')
    ic(main_data_dir)

    reference_picker_config = params.get('reference_picker_config')
    comparison_collector = None
    reference_xml_dir = None
    if reference_picker_config:
        reference_picker_config = os.path.abspath(os.path.expanduser(reference_picker_config))
        if not os.path.exists(reference_picker_config):
            print('\033[91m\n\n\t', end='')
            print(f'WARNING: reference_picker_config path does not exist: {reference_picker_config}')
            print('\tReference comparison disabled.')
            print('\033[0m', end='\n')
        else:
            comparison_collector = ComparisonCollector()
            reference_xml_dir = dir_maker.make_dir(CWD, 'reference_exc_xml')
            print(f'\n\tReference picker comparison enabled with: {reference_picker_config}\n')
    
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

        reference_station_file = None
        if comparison_collector is not None:
            reference_station_file = resolve_reference_station_file(reference_picker_config, net, sta)
            if reference_station_file is None:
                print('\033[91m\n\t', end='')
                print(f'WARNING: No reference station file found for {net}.{sta}.')
                print('\tSkipping reference-vs-best comparison for this station.')
                print('\033[0m', end='\n')

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
        times_paths = waveform_downloader(clients, station, manual_picks, DT,
                                          download_noise_p)

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

            if comparison_collector is None or reference_station_file is None:
                continue

            reference_xml_path = os.path.join(reference_xml_dir,
                                              f'exc_reference_{sta}_{phase}.xml')
            try:
                build_reference_scautopick_xml(reference_station_file,
                                               reference_xml_path,
                                               net,
                                               sta,
                                               loc,
                                               ch_)
                best_y_obs, best_y_pred = evaluate_best_phase(net, sta, phase)
                ref_y_obs, ref_y_pred = evaluate_reference_phase(reference_xml_path)
            except Exception as exc:
                print('\033[91m\n\t', end='')
                print(f'WARNING: Comparison failed for {net}.{sta} {phase}: {exc}')
                print('\033[0m', end='\n')
                continue

            comparison_collector.add(phase, 'best', best_y_obs, best_y_pred)
            comparison_collector.add(phase, 'reference', ref_y_obs, ref_y_pred)

    if comparison_collector is not None:
        print('\n\033[96mOverall reference vs best picker comparison\033[0m')
        print(format_comparison_table(comparison_collector))


def _best_params_from_csv(net: str, sta: str, phase: str) -> dict:
    csv_path = f'results_{phase}.csv'
    df = pd.read_csv(csv_path)
    best_rows = df[df['net.sta'] == f'{net}.{sta}'].sort_values(by='best_f1',
                                                                ascending=False)
    if best_rows.empty:
        raise ValueError(f'No best parameters found in {csv_path} for {net}.{sta}')
    return best_rows.iloc[0].to_dict()


def best_eval_params(net: str, sta: str, phase: str) -> dict:
    p_params = _best_params_from_csv(net, sta, 'P')
    required = ['p_sta', 'p_lta', 'p_fmin', 'p_fmax', 'p_snr', 'trig_on']
    params = {key: p_params[key] for key in required}

    if phase == 'S':
        s_params = _best_params_from_csv(net, sta, 'S')
        params.update({key: s_params[key] for key in ['s_snr', 's_fmin', 's_fmax']})
    return params


def evaluate_best_phase(net: str, sta: str, phase: str):
    stalta = StaLta()
    params = best_eval_params(net, sta, phase)
    return stalta.mega_sta_lta(**params)


def evaluate_reference_phase(reference_xml_path: str):
    stalta = StaLta()
    return stalta.mega_sta_lta(config_db_path=reference_xml_path)

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
