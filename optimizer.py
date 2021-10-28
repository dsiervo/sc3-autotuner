# -*- coding: utf-8 -*-
"""
Created on Sep 2, 2021
@author: Daniel Siervo, emetdan@gmail.com

Application of bayesian optimization using optuna package
"""
import optuna
import plotly
#from sc3autotuner import read_params
from sklearn.metrics import precision_score, recall_score, roc_auc_score, fbeta_score
from stalta import StaLta


def objetive_p(trial, metric='f1'):
    """Función objetivo a minimizar"""
    
    metrics = {
                'f': fbeta_score,
                'pr': precision_score,
                're': recall_score,
                'roc': roc_auc_score
               }
    
    space = {
        'p_sta': trial.suggest_uniform('sta', 0.1, 3),
        'p_sta_width': trial.suggest_loguniform('p_sta_width', 1, 100),
        'p_fmin': trial.suggest_int('f_min', 1, 10),
        'p_fwidth': trial.suggest_int('f_width', 1, 10),
        'p_timecorr': trial.suggest_uniform('p_timecorr', 0, 1),
        'p_snr': trial.suggest_int('p_snr', 1, 4),
        'aic_fmin': trial.suggest_int('aic_fmin', 1, 10),
        'aic_fwidth': trial.suggest_int('aic_fmax', 1, 10),
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
    pass


def bayes_optuna(net, sta, loc, phase, n_trials=1000):

    objective_func = {'P': objetive_p, 'S': objective_s}
    study = optuna.create_study(direction='maximize') #, pruner=optuna.pruners.MedianPruner()
    study.optimize(objective_func['P'], n_trials=n_trials)

    fig_hist = optuna.visualization.plot_optimization_history(study)
    fig_cont = optuna.visualization.plot_contour(study,
                                                 params=['sta', 'p_sta_width'])
    fig_slice = optuna.visualization.plot_slice(study,
                                                params=['sta', 'p_sta_width',
                                                        'f_min', 'f_width',
                                                        'trig_on'])
    fig_parall = optuna.visualization.plot_parallel_coordinate(study,
                                                               params=['sta',
                                                                       'p_sta_width',
                                                                       'f_min',
                                                                       'f_width',
                                                                       'trig_on'])

    print('Number of finished trials: {}'.format(len(study.trials)))

    print('Best trial:')
    trial = study.best_trial

    print('  Value: {}'.format(trial.value))

    print('  Params: ')
    for key, value in trial.params.items():
        print('    {}: {}'.format(key, value))
    
    best = trial.params
    best.update({'best loss': trial.value})
    
    #cfg_par = save_results(best)
    
    #station = cfg_par['station']
    #phase = cfg_par['phase']
    #ch = cfg_par['ch']

    fig_hist.update_layout(font=dict(size=24))

    fig_slice.update_layout(font=dict(size=22))

    plotly.offline.plot(fig_slice,
                        filename=f"images/slice_{net}.{sta}.{loc}_{phase}.html",
                        auto_open=False)
    plotly.offline.plot(fig_hist,
                        filename=f"images/history_{net}.{sta}.{loc}_{phase}.html",
                        auto_open=False)
    plotly.offline.plot(fig_cont,
                        filename=f"images/contour_{net}.{sta}.{loc}_{phase}.html",
                        auto_open=False)
    plotly.offline.plot(fig_parall,
                        filename=f"images/parallel_coord_{net}.{sta}.{loc}_{phase}.html",
                        auto_open=False)
    