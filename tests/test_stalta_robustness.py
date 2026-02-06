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

from stalta import StaLta, XMLPicks


def test_current_exc_parsing_supports_equal_sign_in_value(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    current_exc = tmp_path / 'current_exc.txt'
    current_exc.write_text(
        "times_file = /tmp/a=b_times.csv\n"
        "picks_dir = /tmp/picks\n"
        "inv_xml = /tmp/inv.xml\n"
        "_debug = False\n"
        "net = CM\n"
        "ch = HH\n"
        "loc = 00\n"
        "sta = BAR2\n"
    )
    sta_lta = StaLta()
    assert sta_lta.times_file == '/tmp/a=b_times.csv'


def test_xmlpicks_accepts_non_013_namespace(tmp_path):
    xml_path = tmp_path / 'picks.xml'
    xml_path.write_text(
        """<?xml version="1.0"?>
<seiscomp xmlns="http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10" version="0.10">
  <EventParameters>
    <pick>
      <phaseHint>P</phaseHint>
      <time><value>2020-01-01T00:00:00.000Z</value></time>
    </pick>
  </EventParameters>
</seiscomp>
"""
    )
    picks = XMLPicks(str(xml_path), 'P').get_pick_times()
    assert len(picks) == 1


def test_run_scautopick_uses_subprocess_without_shell(tmp_path):
    sta_lta = StaLta.__new__(StaLta)
    sta_lta.wf_path = str(tmp_path / 'wf.mseed')
    sta_lta.xml_exc_path = str(tmp_path / 'exc.xml')
    sta_lta.inv_xml = str(tmp_path / 'inv.xml')
    sta_lta.picks_dir = str(tmp_path / 'picks')

    class _Result:
        returncode = 0

    with patch('stalta.subprocess.run', return_value=_Result()) as run_mock:
        sta_lta.run_scautopick()

    args, kwargs = run_mock.call_args
    command = args[0]
    assert isinstance(command, list)
    assert command[0] == 'scautopick'
    assert kwargs['check'] is False


def test_match_pick_times_counts_false_picks():
    # Two observed picks; three predictions where one is unmatched.
    observed = [0.0, 10.0]
    predicted = [0.1, 9.9, 30.0]
    counts = StaLta._match_pick_times(observed, predicted, tolerance_seconds=0.25)
    assert counts == {'tp': 2, 'fp': 1, 'fn': 0}
