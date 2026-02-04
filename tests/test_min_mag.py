import sys
import types
from unittest.mock import patch

# Provide a tiny colorama stub so icecream can import without the optional dependency.
if 'colorama' not in sys.modules:
    colorama = types.ModuleType('colorama')
    colorama.Style = types.SimpleNamespace(BRIGHT='', RESET_ALL='')
    colorama.Fore = types.SimpleNamespace(LIGHTCYAN_EX='')
    colorama.init = lambda *args, **kwargs: None
    colorama.deinit = lambda *args, **kwargs: None
    sys.modules['colorama'] = colorama

if 'MySQLdb' not in sys.modules:
    mysqldb = types.ModuleType('MySQLdb')

    class OperationalError(Exception):
        pass

    mysqldb.OperationalError = OperationalError
    sys.modules['MySQLdb'] = mysqldb

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

from icecream import install
install()  # Ensure ic() is available for modules that expect it

import pytest

from config_params import OPTIMIZATION_PARAMS
from download_data import Query
from optimizer import CSVData
from picker_tuner import DirectoryCreator, picker_tuner


class DummyCursor:
    """Minimal cursor mock for Query and picker_tuner."""

    def execute(self, query):
        self.last_query = query

    def fetchall(self):
        return []


class QueryStub:
    """Simple replacement for download_data.Query used inside picker_tuner tests."""

    instances = []

    def __init__(self, cursor, query_type, dic_data):
        self.cursor = cursor
        self.query_type = query_type
        self.dic_data = dic_data
        QueryStub.instances.append(self)

    def execute_query(self):
        if self.query_type == 'station_coords':
            return ['HHZ'], 6.5, -73.18
        # Return enough fake picks so the tuning loop continues
        sample_row = [0, 'event', 'P', '2020-01-01T00:00:00', 0,
                      'S', '2020-01-01T00:00:05', 0]
        return [sample_row for _ in range(5)]


@pytest.fixture(autouse=True)
def _clear_query_stub():
    QueryStub.instances.clear()


def test_picks_query_renders_min_mag():
    cursor = DummyCursor()
    params = {
        'sta_lat': 6.5,
        'sta_lon': -73.1,
        'ti': '2020-01-01T00:00:00',
        'tf': '2020-01-02T00:00:00',
        'net': 'CM',
        'sta': 'BAR2',
        'radius': 200,
        'max_picks': 10,
        'min_mag': 2.5,
    }

    query = Query(cursor=cursor, query_type='picks', dic_data=params).query

    assert f'between "{params["min_mag"]}" and 4.0' in query


def test_picker_tuner_defaults_to_min_mag(tmp_path):
    inv_file = tmp_path / 'scautopick.xml'
    inv_file.write_text('<xml/>')

    params = {
        'radius': '50',
        'inv_xml': str(inv_file),
        'debug': False,
        'n_trials': '1',
        'max_picks': 10,
        'fdsn_ip': 'hostA,hostB',
        'stations': 'CM.BAR2.00.HH',
    }

    def fake_make_dir(self, _root, name):
        path = tmp_path / name
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    fake_times = {'P': str(tmp_path / 'P.csv'),
                  'S': str(tmp_path / 'S.csv')}

    with patch('picker_tuner.Query', QueryStub), \
            patch.object(DirectoryCreator, 'make_dir', fake_make_dir), \
            patch('picker_tuner.waveform_downloader', lambda *args, **kwargs: fake_times), \
            patch('picker_tuner.write_current_exc'), \
            patch('picker_tuner.bayes_optuna'), \
            patch('picker_tuner.obspy.clients.fdsn.Client', lambda *args, **kwargs: object()):
        picker_tuner(cursor=DummyCursor(), wf_cursor=DummyCursor(),
                     ti='2020-01-01', tf='2020-02-01', params=params)

    picks_invocations = [q for q in QueryStub.instances if q.query_type == 'picks']
    assert picks_invocations
    assert picks_invocations[0].dic_data['min_mag'] == pytest.approx(1.2)


def test_picker_tuner_uses_provided_min_mag(tmp_path):
    inv_file = tmp_path / 'scautopick.xml'
    inv_file.write_text('<xml/>')

    params = {
        'radius': '50',
        'inv_xml': str(inv_file),
        'debug': False,
        'n_trials': '1',
        'max_picks': 10,
        'fdsn_ip': 'hostA,hostB',
        'stations': 'CM.BAR2.00.HH',
        'min_mag': '2.7',
    }

    def fake_make_dir(self, _root, name):
        path = tmp_path / name
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    fake_times = {'P': str(tmp_path / 'P.csv'),
                  'S': str(tmp_path / 'S.csv')}

    with patch('picker_tuner.Query', QueryStub), \
            patch.object(DirectoryCreator, 'make_dir', fake_make_dir), \
            patch('picker_tuner.waveform_downloader', lambda *args, **kwargs: fake_times), \
            patch('picker_tuner.write_current_exc'), \
            patch('picker_tuner.bayes_optuna'), \
            patch('picker_tuner.obspy.clients.fdsn.Client', lambda *args, **kwargs: object()):
        picker_tuner(cursor=DummyCursor(), wf_cursor=DummyCursor(),
                     ti='2020-01-01', tf='2020-02-01', params=params)

    picks_invocations = [q for q in QueryStub.instances if q.query_type == 'picks']
    assert picks_invocations
    assert picks_invocations[0].dic_data['min_mag'] == pytest.approx(2.7)


def test_optimizer_config_allows_extended_bandwidth():
    assert OPTIMIZATION_PARAMS['P']['p_fmax']['max'] == 40


def test_csvdata_persists_station_identifier():
    best_params = {
        'p_sta': 0.5,
        'p_lta': 4.5,
        'p_fmin': 2,
        'p_fmax': 7,
        'p_snr': 2,
        'trig_on': 3.0,
        'aic_fmin': 1,
        'aic_fwidth': 1,
        'best_f1': 0.7,
    }
    csv = CSVData('P', best_params, 'XX', 'TEST')
    first_column = csv.values.strip().split(',')[0]
    assert first_column == 'XX.TEST'
