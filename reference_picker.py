"""Helpers for evaluating reference scautopick station configurations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

import numpy as np


SCHEMA_NS = "http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.10"


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_station_picker_params(config_path: str) -> dict:
    """Load a station_NET_STA config file into a key-value dictionary."""
    params = {}
    with open(config_path, "r") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            params[key.strip()] = _strip_quotes(value)
    return params


def resolve_reference_station_file(reference_picker_config: str, net: str, sta: str) -> str:
    """
    Resolve the reference station config file path for a station.
    Supports:
    - direct file path
    - directory containing station_NET_STA files
    """
    reference_picker_config = os.path.abspath(os.path.expanduser(reference_picker_config))
    if not os.path.exists(reference_picker_config):
        return None

    if os.path.isfile(reference_picker_config):
        basename = os.path.basename(reference_picker_config)
        match = re.match(r"^station_([^_]+)_([^_.]+)(?:\..+)?$", basename)
        if match and (match.group(1), match.group(2)) != (net, sta):
            return None
        return reference_picker_config

    candidates = [
        f"station_{net}_{sta}",
        f"station_{net}_{sta}.cfg",
        f"{net}_{sta}",
        f"{net}_{sta}.cfg",
    ]
    for candidate in candidates:
        path = os.path.join(reference_picker_config, candidate)
        if os.path.isfile(path):
            return path
    return None


def _tag(name: str) -> str:
    return f"{{{SCHEMA_NS}}}{name}"


def build_reference_scautopick_xml(
    station_config_file: str,
    output_xml_path: str,
    net: str,
    sta: str,
    loc: str,
    ch: str,
) -> str:
    """
    Build a SeisComP config XML for scautopick using a station_NET_STA file.
    """
    ET.register_namespace("", SCHEMA_NS)
    params = load_station_picker_params(station_config_file)

    detec_stream = params.get("detecStream", ch)
    detec_locid = params.get("detecLocid", loc)
    picker_params = {
        key: value
        for key, value in params.items()
        if key not in {"detecStream", "detecLocid"}
    }
    picker_params.setdefault("trigOff", "1")
    picker_params.setdefault("timeCorr", "0.0")

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    station_base = f"ParameterSet/trunk/Station/{net}/{sta}"
    default_id = f"{station_base}/default"
    pick_id = f"{station_base}/pickbayes"
    gaps_id = f"{station_base}/gaps"

    root = ET.Element(_tag("seiscomp"), version="0.10")
    config = ET.SubElement(root, _tag("Config"))

    pset_default = ET.SubElement(
        config,
        _tag("parameterSet"),
        publicID=default_id,
        created=now,
    )
    ET.SubElement(pset_default, _tag("moduleID")).text = "Config/trunk"
    _append_parameter(pset_default, "detecStream", detec_stream, 0)
    _append_parameter(pset_default, "detecLocid", detec_locid, 1)

    pset_pick = ET.SubElement(
        config,
        _tag("parameterSet"),
        publicID=pick_id,
        created=now,
    )
    ET.SubElement(pset_pick, _tag("baseID")).text = default_id
    ET.SubElement(pset_pick, _tag("moduleID")).text = "Config/trunk"
    for i, (name, value) in enumerate(picker_params.items(), start=2):
        _append_parameter(pset_pick, name, value, i)

    pset_gaps = ET.SubElement(
        config,
        _tag("parameterSet"),
        publicID=gaps_id,
        created=now,
    )
    ET.SubElement(pset_gaps, _tag("baseID")).text = default_id
    ET.SubElement(pset_gaps, _tag("moduleID")).text = "Config/trunk"
    _append_parameter(pset_gaps, "enable", "true", 9999)

    module = ET.SubElement(
        config,
        _tag("module"),
        publicID="Config/trunk",
        name="trunk",
        enabled="true",
    )
    station = ET.SubElement(
        module,
        _tag("station"),
        publicID=f"Config/trunk/{net}/{sta}",
        networkCode=net,
        stationCode=sta,
        enabled="true",
    )
    creation = ET.SubElement(station, _tag("creationInfo"))
    ET.SubElement(creation, _tag("agencyID")).text = "AUTOTUNER"
    ET.SubElement(creation, _tag("author")).text = "sc3-autotuner"
    ET.SubElement(creation, _tag("creationTime")).text = now

    setup_default = ET.SubElement(station, _tag("setup"), name="default", enabled="true")
    ET.SubElement(setup_default, _tag("parameterSetID")).text = default_id
    setup_pick = ET.SubElement(station, _tag("setup"), name="scautopick", enabled="true")
    ET.SubElement(setup_pick, _tag("parameterSetID")).text = pick_id
    setup_gaps = ET.SubElement(station, _tag("setup"), name="gaps", enabled="true")
    ET.SubElement(setup_gaps, _tag("parameterSetID")).text = gaps_id

    out_dir = os.path.dirname(output_xml_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    tree = ET.ElementTree(root)
    write_pretty_xml(tree, output_xml_path)
    return output_xml_path


def _append_parameter(parent, name: str, value: str, idx: int):
    parameter = ET.SubElement(parent, _tag("parameter"), publicID=f"Parameter/reference/{idx}")
    ET.SubElement(parameter, _tag("name")).text = name
    ET.SubElement(parameter, _tag("value")).text = str(value)


def write_pretty_xml(tree: ET.ElementTree, output_xml_path: str):
    """
    Write XML with indentation across Python versions.
    """
    try:
        ET.indent(tree, space="  ")
        tree.write(output_xml_path, encoding="UTF-8", xml_declaration=True)
    except AttributeError:
        raw = ET.tostring(tree.getroot(), encoding='utf-8')
        pretty = minidom.parseString(raw).toprettyxml(indent='  ', encoding='UTF-8')
        with open(output_xml_path, 'wb') as f:
            f.write(pretty)


def compute_binary_metrics(y_obs, y_pred) -> dict:
    """Compute F1, TPR, FPR and confusion matrix from binary arrays."""
    y_obs = np.asarray(y_obs).ravel() > 0.5
    y_pred = np.asarray(y_pred).ravel() > 0.5

    tp = int(np.sum(y_obs & y_pred))
    tn = int(np.sum(~y_obs & ~y_pred))
    fp = int(np.sum(~y_obs & y_pred))
    fn = int(np.sum(y_obs & ~y_pred))

    f1_den = 2 * tp + fp + fn
    tpr_den = tp + fn
    fpr_den = fp + tn

    f1 = (2 * tp / f1_den) if f1_den else 0.0
    tpr = (tp / tpr_den) if tpr_den else 0.0
    fpr = (fp / fpr_den) if fpr_den else 0.0

    return {
        "f1": f1,
        "tpr": tpr,
        "fpr": fpr,
        "confusion": [[tn, fp], [fn, tp]],
    }


def compute_pick_metrics(tp: int, fp: int, fn: int) -> dict:
    """
    Compute pick-level metrics from matched/unmatched pick counts.
    For pick-level reporting TN is not defined, so it is fixed at 0.
    """
    tp = int(tp)
    fp = int(fp)
    fn = int(fn)
    tn = 0

    f1_den = 2 * tp + fp + fn
    tpr_den = tp + fn
    # Pick-level "false positive rate" as false pick proportion.
    fpr_den = fp + tp

    f1 = (2 * tp / f1_den) if f1_den else 0.0
    tpr = (tp / tpr_den) if tpr_den else 0.0
    fpr = (fp / fpr_den) if fpr_den else 0.0

    return {
        "f1": f1,
        "tpr": tpr,
        "fpr": fpr,
        "confusion": [[tn, fp], [fn, tp]],
    }


@dataclass
class ComparisonCollector:
    """Collects per-phase predictions for best-vs-reference reporting."""

    data: dict = field(default_factory=lambda: {
        "P": {"reference": {"tp": 0, "fp": 0, "fn": 0},
              "best": {"tp": 0, "fp": 0, "fn": 0}},
        "S": {"reference": {"tp": 0, "fp": 0, "fn": 0},
              "best": {"tp": 0, "fp": 0, "fn": 0}},
    })

    def add(self, phase: str, label: str, pick_counts: dict):
        bucket = self.data[phase][label]
        bucket["tp"] += int(pick_counts.get("tp", 0))
        bucket["fp"] += int(pick_counts.get("fp", 0))
        bucket["fn"] += int(pick_counts.get("fn", 0))

    def metrics(self, phase: str, label: str):
        bucket = self.data[phase][label]
        if bucket["tp"] == 0 and bucket["fp"] == 0 and bucket["fn"] == 0:
            return None
        return compute_pick_metrics(bucket["tp"], bucket["fp"], bucket["fn"])


def format_comparison_table(collector: ComparisonCollector) -> str:
    """Render an aligned table for P and S overall comparison."""
    header = "Phase  Config      F1      TPR      FPR(FP/(TP+FP))   Confusion [TN FP; FN TP]"
    rows = [header, "-" * len(header)]

    for phase in ("P", "S"):
        for label in ("reference", "best"):
            metrics = collector.metrics(phase, label)
            if metrics is None:
                continue
            confusion = metrics["confusion"]
            cm_str = f"[{confusion[0][0]} {confusion[0][1]}; {confusion[1][0]} {confusion[1][1]}]"
            rows.append(
                f"{phase:<5}  {label:<9}  {metrics['f1']:.4f}  {metrics['tpr']:.4f}  {metrics['fpr']:.4f}  {cm_str}"
            )

    if len(rows) == 2:
        rows.append("No comparable reference-vs-best evaluation samples were collected.")

    return "\n".join(rows)
