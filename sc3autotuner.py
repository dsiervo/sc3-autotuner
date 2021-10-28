#!/usr/bin/env python3
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


def main():
    """Read parmas, choose in wich modules will be
    tuned, and run it
    """
    # default parameters
    params = {'debug': False, 'max_picks': 50, 'n_trials': 100}
    
    params_new = read_params()
    
    # update params
    params.update(params_new)
    
    params['debug'] = True if params['debug'] in ['true', 'True', 'TRUE'] else False
    
    if not params['debug']:
        ic.disable()
    else:
        ic.enable()
    try:
        db_ip = params['db_ip']
        tune_mode = params['tune_mode']
        ti = params['ti']
        tf = params['tf']
    except KeyError:
        print('\n\n\tERROR! db_ip, tune_mode, ti or tf no defined in sc3-autotuner.inp\n\n')
        sys.exit()
    
    db = MySQLdb.connect(host=db_ip,
                         user='consulta',
                         passwd='consulta',
                         db='seiscomp3')

    cursor = db.cursor()
    
    # choose in which way the program will be runned
    if tune_mode in ['picker', 'piker', 'picer', 'Picker']:
        ic(ti)
        ic(tf)
        ic(cursor)
         
        picker_tuner(cursor, ti, tf, params)
        
    elif tune_mode in ['associator', 'asociator', 'Associator']:
        # run assoc_tuner.py
        pass
    else:
        print(f'\n\n\tThe option {tune_mode} you have entered is not a valid option for tune_mode.')
        print('\tShould be: picker or associator\n\n')
        sys.exit()
        
    
    # Run picker and assoc tunners


def read_params(par_file='sc3-autotuner.inp'):
    lines = open(par_file).readlines()
    par_dic = {}
    for line in lines:
        if line[0] == '#' or line.strip('\n').strip() == '':
            continue
        else:
            l = line.strip('\n').strip()
            key, value = l.split('=')
            par_dic[key.strip()] = value.strip()
    return par_dic


if __name__ == '__main__':
    main()
    