import os
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

from picker_tuner import (
    event_ids_from_times_file,
    waveform_paths_from_times_file,
    write_station_comparison_report,
)
from reference_picker import ComparisonCollector


def test_event_ids_from_times_file_excludes_noise(tmp_path):
    times_file = tmp_path / 'GV02_P_HH.txt'
    times_file.write_text(
        "/tmp/eventA.GV02.00.HH_20250101T000000.mseed,2025-01-01T00:00:00,2025-01-01T00:00:00,100,2000\n"
        "/tmp/eventA.GV02.00.HH_20250101T000001.mseed,2025-01-01T00:00:01,2025-01-01T00:00:00,100,2000\n"
        "/tmp/eventB_NOISE.GV02.00.HH_20250101T000100.mseed,NO_PICK,2025-01-01T00:00:00,100,2000\n"
        "/tmp/eventC.GV02.00.HH_20250101T000200.mseed,2025-01-01T00:00:02,2025-01-01T00:00:00,100,2000\n"
    )

    event_ids = event_ids_from_times_file(str(times_file), 'GV02', '00', 'HH')
    assert event_ids == ['eventA', 'eventC']

    waveforms = waveform_paths_from_times_file(str(times_file))
    assert len(waveforms) == 4
    assert waveforms[0].endswith('eventA.GV02.00.HH_20250101T000000.mseed')
    assert waveforms[2].endswith('eventB_NOISE.GV02.00.HH_20250101T000100.mseed')


def test_write_station_comparison_report_file_name_and_content(tmp_path):
    collector = ComparisonCollector()
    collector.add('P', 'reference', {'tp': 3, 'fp': 2, 'fn': 1})
    collector.add('P', 'best', {'tp': 4, 'fp': 1, 'fn': 0})
    collector.add('S', 'reference', {'tp': 1, 'fp': 1, 'fn': 2})
    collector.add('S', 'best', {'tp': 2, 'fp': 1, 'fn': 1})

    path = write_station_comparison_report(
        collector=collector,
        net='4O',
        sta='GV02',
        radius=50,
        ti='2025-10-15 00:00:00',
        tf='2025-10-25 23:59:59',
        max_picks=5,
        n_trials=20,
        phase_event_ids={'P': ['evt1', 'evt2'], 'S': ['evt1', 'evt3']},
        phase_waveforms={
            'P': [
                '/tmp/evt1.GV02.00.HH_20251015T010101.mseed',
                '/tmp/evt1_NOISE.GV02.00.HH_20251015T005901.mseed',
            ],
            'S': ['/tmp/evt3.GV02.00.HH_20251015T020202.mseed'],
        },
        best_xml_paths={
            'P': '/tmp/exc_best_4O_GV02_P.xml',
            'S': '/tmp/exc_best_4O_GV02_S.xml',
        },
        reference_xml_paths={
            'P': '/tmp/exc_reference_4O_GV02_P.xml',
            'S': '/tmp/exc_reference_4O_GV02_S.xml',
        },
        inv_xml='/tmp/inventory.xml',
        loc='00',
        ch='HH',
        output_dir=str(tmp_path),
    )

    assert os.path.isfile(path)
    basename = os.path.basename(path)
    assert basename.startswith('4O_GV02_50_2025-10-15T000000_2025-10-25T235959_5_20')
    assert os.path.isdir(tmp_path / 'replay_picks' / '4O_GV02' / 'P')
    assert os.path.isdir(tmp_path / 'replay_picks' / '4O_GV02' / 'S')

    with open(path, 'r') as f:
        content = f.read()
    assert 'P event_ids (2):' in content
    assert 'evt1,evt2' in content
    assert 'scautopick commands using best XML' in content
    assert '--config-db /tmp/exc_best_4O_GV02_P.xml' in content
    assert '; scrttv /tmp/evt1.GV02.00.HH_20251015T010101.mseed -i ' in content
    assert 'scautopick commands using reference XML (P pick waveforms)' in content
    assert '--config-db /tmp/exc_reference_4O_GV02_P.xml' in content
    assert '_reference_picks.xml' in content
    assert 'evt1_NOISE.GV02.00.HH_20251015T005901.mseed' in content
    assert 'Overall reference vs best picker comparison' in content
    assert 'reference' in content
    assert 'best' in content
