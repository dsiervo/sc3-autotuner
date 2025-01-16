# -*- coding: utf-8 -*-
"""
Created on Sep 2, 2021
@author: Daniel Siervo, emetdan@gmail.com

Application of bayesian optimization using optuna package
"""
from dataclasses import dataclass
import optuna
import plotly
#from sc3autotuner import read_params
from sklearn.metrics import precision_score, recall_score, roc_auc_score, fbeta_score
from stalta import StaLta
import pandas as pd
import os


def objetive_p(trial, metric='f1'):
    """Función objetivo a minimizar"""
    
    metrics = {
                'f': fbeta_score,
                'pr': precision_score,
                're': recall_score,
                'roc': roc_auc_score
               }
    
    space = {
        'p_sta': trial.suggest_float('p_sta', 0.1, 3, step=0.01),
        'p_sta_width': trial.suggest_float('p_sta_width', 1, 100, step=0.01),
        'p_fmin': trial.suggest_int('p_fmin', 1, 10),
        'p_fwidth': trial.suggest_int('p_fwidth', 1, 10),
        'p_timecorr': trial.suggest_float('p_timecorr', 0, 1, step=0.01),
        'p_snr': trial.suggest_int('p_snr', 1, 4),
        'aic_fmin': trial.suggest_int('aic_fmin', 1, 10),
        'aic_fwidth': trial.suggest_int('aic_fwidth', 1, 10),
        'trig_on': trial.suggest_float('trig_on', 2, 15, step=0.01)
           }

    """stalta_params = {'p_sta': 0.1, 'p_lta': 5.7, 'p_fmin': 2,
                     'p_fmax': 8, 'p_timecorr': 0.25, 'p_snr': 3,
                     'aic_fmin': 2, 'aic_fmax': 8, 'trig_on': 5}"""
    
    stalta = StaLta()
    y_obs, y_pred = stalta.mega_sta_lta(**space)
    
    if metric == 'roc':
        score = metrics[metric](y_obs, y_pred)
    elif metric[0] == 'f':
        beta = float(metric.split('f')[1])
        score = metrics['f'](y_obs, y_pred, beta=beta, average='binary')
    else:
        score = metrics[metric](y_obs, y_pred, average='binary')
    
    return score


def objective_s(trial, metric='f1'):
    """Función objetivo a minimizar"""
    
    metrics = {
                'f': fbeta_score,
                'pr': precision_score,
                're': recall_score,
                'roc': roc_auc_score
               }
    
    space = {
        's_fmin': trial.suggest_int('s_fmin', 1, 10),
        's_fwidth': trial.suggest_int('s_fwidth', 1, 10),
        's_snr': trial.suggest_float('s_snr', 1, 4, step=0.01)
           }

    """stalta_params = {'p_sta': 0.1, 'p_lta': 5.7, 'p_fmin': 2,
                     'p_fmax': 8, 'p_timecorr': 0.25, 'p_snr': 3,
                     'aic_fmin': 2, 'aic_fmax': 8, 'trig_on': 5}"""
    
    stalta = StaLta()
    space.update(stalta.best_p_params)
    ic(space)
    y_obs, y_pred = stalta.mega_sta_lta(**space)
    
    if metric == 'roc':
        score = metrics[metric](y_obs, y_pred)
    elif metric[0] == 'f':
        beta = float(metric.split('f')[1])
        score = metrics['f'](y_obs, y_pred, beta=beta, average='binary')
    else:
        score = metrics[metric](y_obs, y_pred, average='binary')
    
    return score


def bayes_optuna(net, sta, loc, ch, phase, n_trials=1000):

    objective_func = {'P': objetive_p, 'S': objective_s}
    
    ## Print in green color the station and the phase to be analyzed
    print(f'\n\n\t\t\t\033[92m{net}.{sta} - {phase}\033[0m\n')    
    
    study = optuna.create_study(direction='maximize') #, pruner=optuna.pruners.MedianPruner()
    study.optimize(objective_func[phase], n_trials=n_trials)
    
    # plotting and writing results in csv file and in config file
    plot_and_write = PlotWrite(net, sta, loc, ch, phase, study)
    plot_and_write.plot_and_write()


@dataclass
class CSVData:
    phase: str
    best_params: dict
    net: str
    sta: str
    
    @property
    def header(self):
        if self.phase == 'P':
            line = ','.join(['net.sta', 'p_sta', 'p_sta_width', 'p_fmin',
                              'p_fwidth', 'aic_fmin', 'aic_fwidth', 'p_timecorr',
                              'p_snr', 'trig_on', 'best_f1\n'])
            return line
        elif self.phase == 'S':
            return 'net.sta,s_fmin,s_fwidth,s_snr,best_f1\n'
    
    @property
    def values(self):
        if self.phase == 'P':
            line = f'{self.net}.{self.sta},{self.best_params["p_sta"]},'
            line += f'{self.best_params["p_sta_width"]},{self.best_params["p_fmin"]},'
            line += f'{self.best_params["p_fwidth"]},{self.best_params["aic_fmin"]},'
            line += f'{self.best_params["aic_fwidth"]},{self.best_params["p_timecorr"]},'
            line += f'{self.best_params["p_snr"]},{self.best_params["trig_on"]},{self.best_params["best_f1"]}\n'
            return line
        elif self.phase == 'S':
            return f'{self.net}.{self.sta},{self.best_params["s_fmin"]},{self.best_params["s_fwidth"]},{self.best_params["s_snr"]},{self.best_params["best_f1"]}\n'


class PlotWrite:
    net: str
    sta: str
    loc: str
    phase: str
    ch: str
    study: optuna.study.Study
    main_dir: str = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, net, sta, loc, ch, phase, study):
        self.net = net
        self.sta = sta
        self.loc = loc
        self.ch = ch
        self.phase = phase
        self.study = study

    def plot_and_write(self):
        fig_hist = optuna.visualization.plot_optimization_history(self.study)
        params = {'P': ['p_sta', 'p_sta_width', 'p_fmin', 'p_fwidth', 'trig_on'],
                'S': ['s_fmin', 's_fwidth', 's_snr']}
        
        #fig_cont = optuna.visualization.plot_contour(study,
        #                                             params=['p_sta', 'p_sta_width'])
        fig_slice = optuna.visualization.plot_slice(self.study,
                                                    params=params[self.phase])
        fig_parall = optuna.visualization\
                    .plot_parallel_coordinate(self.study,
                                            params=params[self.phase])

        print(f'\n\n\033[92m{self.net}.{self.sta} - {self.phase}\033[0m')
        print('Number of finished trials: {}'.format(len(self.study.trials)))

        print('Best trial:')
        trial = self.study.best_trial

        print('  Best f1-score {}'.format(trial.value))

        print('  Params: ')
        for key, value in trial.params.items():
            print('    {}: {}'.format(key, value))
        
        best = trial.params
        best.update({'best_f1': trial.value})

        fig_hist.update_layout(font=dict(size=24))

        fig_slice.update_layout(font=dict(size=22))

        plotly.offline.plot(fig_slice,
                            filename=f"images/slice_{self.net}.{self.sta}.{self.loc}_{self.phase}.html",
                            auto_open=False)
        plotly.offline.plot(fig_hist,
                            filename=f"images/history_{self.net}.{self.sta}.{self.loc}_{self.phase}.html",
                            auto_open=False)
        #plotly.offline.plot(fig_cont,
        #                    filename=f"images/contour_{self.net}.{self.sta}.{self.loc}_{self.phase}.html",
        #                    auto_open=False)
        plotly.offline.plot(fig_parall,
                            filename=f"images/parallel_coord_{self.net}.{self.sta}.{self.loc}_{self.phase}.html",
                            auto_open=False)

        # write best params to .csv file
        self.write_best_csv(best)
        # write best params to self.station_CM_template config file if phase is S
        if self.phase == 'S':
            self.write_config_file()

    def write_best_csv(self, best_params):
        """Write best params to .csv file
           if the file already exists, append the new line
           else create a new file"""
        csv_data = CSVData(self.phase, best_params, self.net, self.sta)
        
        results_file = f'results_{self.phase}.csv'
        if not os.path.exists(results_file):
            with open(results_file, 'w') as f:
                f.write(csv_data.header)
        with open(results_file, 'a') as f:
            f.write(csv_data.values)

    @property
    def config_file_template(self):
        return os.path.join(self.main_dir, 'bindings', 'station_NET_template')

    @property
    def out_dir(self):
        return os.path.join('output_station_files')

    @property
    def config_output_file(self):
        return os.path.join(self.out_dir, f'station_{self.net}_{self.sta}')
    
    def write_config_file(self):
        """
        Write the best params to the station_NET_template config file
        """
        
        if not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)
        
        # get optimized pick params from results_P.csv and results_S.csv
        params_ = self.get_params_from_csv()
        params = self.fix_params(params_)
        
        # write to config file
        template = open(self.config_file_template, 'r').read()
        with open(self.config_output_file, 'w') as f:
            f.write(template.format(**params))
    
    def get_params_from_csv(self):
        params = self.get_p_params()
        params.update(self.get_s_params())
        params.update({'ch': self.ch, 'loc': self.loc})
        return params
    
    def get_p_params(self):
        """
        Get pick params from results_P.csv
        """
        return self.get_params_from_csv_file('P')
    
    def get_s_params(self):
        """
        Get pick params from results_S.csv
        """
        return self.get_params_from_csv_file('S')
    
    def get_params_from_csv_file(self, phase):
        """
        Get best pick params from results_P.csv or results_S.csv
        """
        df = pd.read_csv(f'results_{phase}.csv')
        # selecting the row with net.sta equal to CM.BAR2 and with the highest value of best_f1
        return df[df['net.sta'] == f'{self.net}.{self.sta}'].sort_values(by='best_f1', ascending=False).iloc[0].to_dict()

    def fix_params(self, params):
        # rename params to match the station_NET_template config file
        # p_sta_width, p_fwidth, aic_fwidth and s_fwidth
        #rename_dict = {'p_sta_width': 'p_lta', 'p_fwidth': 'p_fmax', 'aic_fwidth': 'aic_fmax', 's_fwidth': 's_fmax'}
        
        params['p_fmax'] = params['p_fmin'] + params['p_fwidth']
        params['p_lta'] = params['p_sta'] + params['p_sta_width']
        params['aic_fmax'] = params['aic_fmin'] + params['aic_fwidth']
        params['s_fmax'] = params['s_fmin'] + params['s_fwidth']

        """for key in rename_dict:
            if key in params:
                params[rename_dict[key]] = params.pop(key)"""
        
        return params