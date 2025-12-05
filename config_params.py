# Optimization ranges, steps and types for parameters
OPTIMIZATION_PARAMS = {
    'P': {
        'p_sta': {'min': 0.1, 'max': 3, 'step': 0.01, 'type': 'float'},
        'p_sta_width': {'min': 1, 'max': 100, 'step': 0.01, 'type': 'float'},
        'p_fmin': {'min': 1, 'max': 10, 'step': 1, 'type': 'int'},
        'p_fwidth': {'min': 1, 'max': 30, 'step': 1, 'type': 'int'},
        'p_snr': {'min': 1, 'max': 4, 'step': 1, 'type': 'int'},
        'trig_on': {'min': 2, 'max': 15, 'step': 0.01, 'type': 'float'}
    },
    'S': {
        's_snr': {'min': 1, 'max': 4, 'step': 0.01, 'type': 'float'},
        's_fmin': {'min': 0.1, 'max': 10, 'step': 0.1, 'type': 'float'},
        's_fwidth': {'min': 1, 'max': 15, 'step': 0.1, 'type': 'float'}
    }
}

# Default values for fixed parameters
DEFAULT_VALUES = {
    'p_timecorr': 0.0,
    'aic_fmin': 1,
    'aic_fwidth': 0,
    'picker_aic_filter': 'ITAPER(1)>>BW_HP(3,2)'
}

# CSV file headers
CSV_HEADERS = {
    'P': ['net.sta', 'p_sta', 'p_sta_width', 'p_fmin', 'p_fwidth', 
          'aic_fmin', 'aic_fwidth', 'p_timecorr', 'p_snr', 'trig_on', 'best_f1'],
    'S': ['net.sta', 's_fmin', 's_fwidth', 's_snr', 'best_f1']
}

# Parameters to plot in optimization visualizations
PLOT_PARAMS = {
    'P': ['p_sta', 'p_sta_width', 'p_fmin', 'p_fwidth', 'p_snr', 'trig_on'],
    'S': ['s_snr', 's_fmin', 's_fwidth']
}
