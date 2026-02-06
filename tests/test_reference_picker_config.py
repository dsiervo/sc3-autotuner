import xml.etree.ElementTree as ET

import pytest

from reference_picker import (
    ComparisonCollector,
    build_reference_scautopick_xml,
    compute_binary_metrics,
    format_comparison_table,
    load_station_picker_params,
    resolve_reference_station_file,
)


def test_load_station_picker_params_strips_quotes_and_comments(tmp_path):
    station_file = tmp_path / "station_CM_BAR2"
    station_file.write_text(
        "# comment\n"
        "detecStream = HH\n"
        "detecLocid = 00\n"
        "detecFilter = \"BW(4,2,8)>>STALTA(1,10)\"\n"
        "trigOn = 3.5\n"
    )

    params = load_station_picker_params(str(station_file))

    assert params["detecStream"] == "HH"
    assert params["detecLocid"] == "00"
    assert params["detecFilter"] == "BW(4,2,8)>>STALTA(1,10)"
    assert params["trigOn"] == "3.5"


def test_resolve_reference_station_file_for_directory_and_file(tmp_path):
    station_file = tmp_path / "station_CM_BAR2"
    station_file.write_text("trigOn = 3.0\n")

    assert resolve_reference_station_file(str(tmp_path), "CM", "BAR2") == str(station_file)
    assert resolve_reference_station_file(str(tmp_path), "CM", "NOPE") is None
    assert resolve_reference_station_file(str(station_file), "CM", "BAR2") == str(station_file)
    assert resolve_reference_station_file(str(station_file), "CM", "NOPE") is None


def test_build_reference_scautopick_xml_contains_station_and_picker_params(tmp_path):
    station_file = tmp_path / "station_CM_BAR2"
    station_file.write_text(
        "detecStream = HH\n"
        "detecLocid = 00\n"
        "trigOn = 4.0\n"
        "picker.AIC.minSNR = 3\n"
    )
    out_xml = tmp_path / "exc_reference_BAR2_P.xml"

    build_reference_scautopick_xml(str(station_file), str(out_xml), "CM", "BAR2", "00", "HH")

    tree = ET.parse(str(out_xml))
    root = tree.getroot()
    ns = {"sc": root.tag[root.tag.find("{") + 1:root.tag.find("}")]}

    station_nodes = root.findall(".//sc:station", ns)
    assert station_nodes and station_nodes[0].attrib["networkCode"] == "CM"
    assert station_nodes[0].attrib["stationCode"] == "BAR2"

    name_values = {
        node.find("sc:name", ns).text: node.find("sc:value", ns).text
        for node in root.findall(".//sc:parameter", ns)
    }
    assert name_values["detecStream"] == "HH"
    assert name_values["detecLocid"] == "00"
    assert name_values["trigOn"] == "4.0"
    assert name_values["picker.AIC.minSNR"] == "3"


def test_compute_binary_metrics_and_table():
    y_obs = [1, 1, 0, 0]
    y_pred = [1, 0, 1, 0]
    metrics = compute_binary_metrics(y_obs, y_pred)

    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["tpr"] == pytest.approx(0.5)
    assert metrics["fpr"] == pytest.approx(0.5)
    assert metrics["confusion"] == [[1, 1], [1, 1]]

    collector = ComparisonCollector()
    collector.add("P", "reference", y_obs, y_pred)
    collector.add("P", "best", y_obs, y_obs)
    table = format_comparison_table(collector)
    assert "Phase" in table
    assert "reference" in table
    assert "best" in table
