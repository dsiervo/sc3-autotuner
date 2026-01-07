#!/home/seiscomp/sc3-autotuner/venv/bin/python
# -*- coding: utf-8 -*-
"""
Created on Jun 24 2021

@author: Daniel Siervo, emetdan@gmail.com
"""
import os
import sys
import MySQLdb
from picker_tuner import picker_tuner
from icecream import ic
ic.configureOutput(prefix='debug| ')


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in ['true', '1', 'yes']


def main():
    """Read parmas, choose in wich modules will be
    tuned, and run it
    """
    # default parameters
    params = {'debug': False, 'max_picks': 50, 'n_trials': 100}
    
    params_new = read_params()

    download_noise_raw = params_new.get('download_noise_p')
    if download_noise_raw is None:
        download_noise_flag = False
        print("\n\tParameter 'download_noise_p' not set. Using default value False for P-phase noise downloads.\n")
    else:
        download_noise_flag = parse_bool(download_noise_raw)
        print(f"\n\tParameter 'download_noise_p' set to {download_noise_flag} for P-phase noise downloads.\n")
    params_new['download_noise_p'] = download_noise_flag
    
    # update params
    params.update(params_new)
    
    params['debug'] = parse_bool(params.get('debug', False))
    
    if not params['debug']:
        ic.disable()
    else:
        ic.enable()
    try:
        deb_url = params['deb_url']
        tune_mode = params['tune_mode']
        ti = params['ti']
        tf = params['tf']
        sql_usr = params['sql_usr']
        sql_psw = params['sql_psw']
    except KeyError:
        print('\n\n\tERROR! deb_url, tune_mode, ti, tf, sql_usr or sql_psw no defined in sc3-autotuner.inp\n\n')
        sys.exit()
    
    try:
        wf_sql_usr = params['wf_sql_usr']
        wf_sql_psw = params['wf_sql_psw']
        wf_url = params['wf_url']
        
        wf_db = MySQLdb.connect(host=wf_url,
                                user=wf_sql_usr,
                                passwd=wf_sql_psw,
                                db='seiscomp')
        wf_cursor = wf_db.cursor()
    except KeyError:
        print('\n\n\tWARNING! wf_url, wf_sql_usr or wf_sql_psw no defined in sc3-autotuner.inp using default deb_url DB to extract station data.\n\n')
        wf_cursor = False
    except MySQLdb.OperationalError:
        print(f'\n\n\tERROR! Impossible to connect to seiscomp DB {wf_url} with user {wf_sql_usr} and passwd {wf_sql_psw}.\n\n')
        wf_cursor = False
    
    # user and passwd have to be a variable
    db = MySQLdb.connect(host=deb_url,
                         user=sql_usr,
                         passwd=sql_psw,
                         db='seiscomp')

    cursor = db.cursor()

    
    # choose in which way the program will be runned
    if tune_mode in ['picker', 'piker', 'picer', 'Picker']:
        ic(ti)
        ic(tf)
        ic(cursor)
         
        picker_tuner(cursor, wf_cursor, ti, tf, params)
        
    elif tune_mode in ['associator', 'asociator', 'Associator']:
        # run assoc_tuner.py
        pass
    else:
        print(f'\n\n\tThe option {tune_mode} you have entered is not a valid option for tune_mode.')
        print('\tShould be: picker or associator\n\n')
        sys.exit()
        
    
def get_param(param_name, params):
    try:
        param_val = params[param_name]
        return param_val
    except KeyError:
        print(f'\n\n\tERROR! {param_name} no defined in sc3-autotuner.inp\n\n')
        sys.exit()


def read_params(par_file='sc3-autotuner.inp'):
    par_dic = {}
    with open(par_file) as f:
        for line in f:
            if line[0] == '#' or line.strip('\n').strip() == '':
                continue
            l = line.strip('\n').strip()
            key, value = l.split('=', 1)
            par_dic[key.strip()] = value.strip()
    return par_dic


if __name__ == '__main__':
    main()
    
