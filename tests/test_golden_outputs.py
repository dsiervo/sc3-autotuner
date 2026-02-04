import csv
import sys
import types

# Provide tiny stubs for optional dependencies used during imports.
if 'colorama' not in sys.modules:
    colorama = types.ModuleType('colorama')
    colorama.Style = types.SimpleNamespace(BRIGHT='', RESET_ALL='')
    colorama.Fore = types.SimpleNamespace(LIGHTCYAN_EX='')
    colorama.init = lambda *args, **kwargs: None
    colorama.deinit = lambda *args, **kwargs: None
    sys.modules['colorama'] = colorama

if 'plotly' not in sys.modules:
    plotly = types.ModuleType('plotly')
    plotly.offline = types.SimpleNamespace(plot=lambda *args, **kwargs: None)
    sys.modules['plotly'] = plotly

if 'sklearn' not in sys.modules:
    sklearn = types.ModuleType('sklearn')
    metrics = types.ModuleType('sklearn.metrics')

    def _dummy_metric(*_args, **_kwargs):
        return 0.0

    metrics.precision_score = _dummy_metric
    metrics.recall_score = _dummy_metric
    metrics.roc_auc_score = _dummy_metric
    metrics.fbeta_score = _dummy_metric

    sklearn.metrics = metrics
    sys.modules['sklearn'] = sklearn
    sys.modules['sklearn.metrics'] = metrics

from config_params import render_config_param_templates
from optimizer import CSVData


def test_render_config_param_templates_golden():
    params = {
        'ch': 'HH',
        'loc': '00',
        'p_sta': 0.5,
        'p_lta': 3.0,
        'p_fmin': 2,
        'p_fmax': 8,
        'p_snr': 2,
        'trig_on': 3.5,
        's_snr': 2.0,
        's_fmin': 1.0,
        's_fmax': 4.0,
        'p_timecorr': 0.0,
        'aic_fmin': 1,
        'aic_fwidth': 0,
        'picker_aic_filter': 'ITAPER(1)>>BW_HP(3,2)',
    }

    rendered = render_config_param_templates(params)

    assert rendered['detecFilter'] == 'RMHP(10)>>ITAPER(30)>>BW(4,2,8)>>STALTA(0.50,3.00)'
    assert rendered['spicker.AIC.filter'] == 'ITAPER(1)>>BW(4,1.0,4.0)'
    assert rendered['spicker_aic_filter'] == 'ITAPER(1)>>BW(4,1.0,4.0)'


def test_csvdata_values_golden(tmp_path):
    best_params = {
        'p_sta': 0.5,
        'p_lta': 4.5,
        'p_fmin': 2,
        'p_fmax': 7,
        'p_snr': 2,
        'trig_on': 3.0,
        'best_f1': 0.7,
    }
    csv_data = CSVData('P', best_params, 'XX', 'TEST')
    out_path = tmp_path / 'results_P.csv'

    with out_path.open('w', newline='') as f:
        f.write(csv_data.header)
        f.write(csv_data.values)

    with out_path.open(newline='') as f:
        rows = list(csv.DictReader(f))

    assert rows == [
        {
            'net.sta': 'XX.TEST',
            'p_sta': '0.5',
            'p_lta': '4.5',
            'p_fmin': '2',
            'p_fmax': '7',
            'p_snr': '2',
            'trig_on': '3.0',
            'best_f1': '0.7',
        }
    ]
