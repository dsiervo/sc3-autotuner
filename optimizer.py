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
        'p_sta': trial.suggest_uniform('p_sta', 0.1, 3),
        'p_sta_width': trial.suggest_loguniform('p_sta_width', 1, 100),
        'p_fmin': trial.suggest_int('p_fmin', 1, 10),
        'p_fwidth': trial.suggest_int('p_fwidth', 1, 10),
        'p_timecorr': trial.suggest_uniform('p_timecorr', 0, 1),
        'p_snr': trial.suggest_int('p_snr', 1, 4),
        'aic_fmin': trial.suggest_int('aic_fmin', 1, 10),
        'aic_fwidth': trial.suggest_int('aic_fwidth', 1, 10),
        'trig_on': trial.suggest_uniform('trig_on', 2, 15)
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
        's_snr': trial.suggest_uniform('s_snr', 1, 4)
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


def bayes_optuna(net, sta, loc, phase, n_trials=1000):

    objective_func = {'P': objetive_p, 'S': objective_s}
    
    ## Print in green color the station and the phase to be analyzed
    print(f'\n\n\t\t\t\033[92m{net}.{sta} - {phase}\033[0m\n')    
    
    study = optuna.create_study(direction='maximize') #, pruner=optuna.pruners.MedianPruner()
    study.optimize(objective_func[phase], n_trials=n_trials)
    plot_and_write(net, sta, loc, phase, study)


def plot_and_write(net, sta, loc, phase, study):
    fig_hist = optuna.visualization.plot_optimization_history(study)
    params = {'P': ['p_sta', 'p_sta_width', 'p_fmin', 'p_fwidth', 'trig_on'],
              'S': ['s_fmin', 's_fwidth', 's_snr']}
    
    #fig_cont = optuna.visualization.plot_contour(study,
    #                                             params=['p_sta', 'p_sta_width'])
    fig_slice = optuna.visualization.plot_slice(study,
                                                params=params[phase])
    fig_parall = optuna.visualization\
                 .plot_parallel_coordinate(study,
                                           params=params[phase])

    print(f'\n\n\033[92m{net}.{sta} - {phase}\033[0m')
    print('Number of finished trials: {}'.format(len(study.trials)))

    print('Best trial:')
    trial = study.best_trial

    print('  Value: {}'.format(trial.value))

    print('  Params: ')
    for key, value in trial.params.items():
        print('    {}: {}'.format(key, value))
    
    best = trial.params
    best.update({'best_loss': trial.value})
    
    # write best params to .csv file
    # if the file already exists, append the new line
    # else create a new file
    write_best_csv(best, net, sta, phase)

    fig_hist.update_layout(font=dict(size=24))

    fig_slice.update_layout(font=dict(size=22))

    plotly.offline.plot(fig_slice,
                        filename=f"images/slice_{net}.{sta}.{loc}_{phase}.html",
                        auto_open=False)
    plotly.offline.plot(fig_hist,
                        filename=f"images/history_{net}.{sta}.{loc}_{phase}.html",
                        auto_open=False)
    #plotly.offline.plot(fig_cont,
    #                    filename=f"images/contour_{net}.{sta}.{loc}_{phase}.html",
    #                    auto_open=False)
    plotly.offline.plot(fig_parall,
                        filename=f"images/parallel_coord_{net}.{sta}.{loc}_{phase}.html",
                        auto_open=False)


def write_best_csv(best_params, net, sta, phase):
    """Write best params to .csv file"""
    csv_data = CSVData(phase, best_params, net, sta)
    
    results_file = f'results_{phase}.csv'
    if not os.path.exists(results_file):
        with open(results_file, 'w') as f:
            f.write(csv_data.header)
    with open(results_file, 'a') as f:
        f.write(csv_data.values)

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
                              'p_snr', 'trig_on', 'best_loss\n'])
            return line
        elif self.phase == 'S':
            return 'net.sta,s_fmin,s_fwidth,s_snr,best_loss\n'
    
    @property
    def values(self):
        if self.phase == 'P':
            line = f'{self.net}.{self.sta},{self.best_params["p_sta"]},'
            line += f'{self.best_params["p_sta_width"]},{self.best_params["p_fmin"]},'
            line += f'{self.best_params["p_fwidth"]},{self.best_params["aic_fmin"]},'
            line += f'{self.best_params["aic_fwidth"]},{self.best_params["p_timecorr"]},'
            line += f'{self.best_params["p_snr"]},{self.best_params["trig_on"]},{self.best_params["best_loss"]}\n'
            return line
        elif self.phase == 'S':
            return f'{self.net}.{self.sta},{self.best_params["s_fmin"]},{self.best_params["s_fwidth"]},{self.best_params["s_snr"]},{self.best_params["best_loss"]}\n'
    
    