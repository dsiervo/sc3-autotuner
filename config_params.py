# Optimization ranges, steps and types for parameters
import string
p_sta_name = 'p_sta'
p_sta_width_name = 'p_sta_width'
p_fmin_name = 'p_fmin'
p_fwidth_name = 'p_fwidth'
p_snr_name = 'p_snr'
trig_on_name = 'trig_on'
s_snr_name = 's_snr'
s_fmin_name = 's_fmin'
s_fwidth_name = 's_fwidth'
OPTIMIZATION_PARAMS = {
    'P': {
        p_sta_name: {'min': 0.1, 'max': 3, 'step': 0.01, 'type': 'float'},
        p_sta_width_name: {'min': 1, 'max': 100, 'step': 0.01, 'type': 'float'},
        p_fmin_name: {'min': 1, 'max': 10, 'step': 1, 'type': 'int'},
        p_fwidth_name: {'min': 1, 'max': 30, 'step': 1, 'type': 'int'},
        p_snr_name: {'min': 1, 'max': 4, 'step': 1, 'type': 'int'},
        trig_on_name: {'min': 2, 'max': 15, 'step': 0.01, 'type': 'float'}
    },
    'S': {
        s_snr_name: {'min': 1, 'max': 4, 'step': 0.01, 'type': 'float'},
        s_fmin_name: {'min': 0.1, 'max': 10, 'step': 0.1, 'type': 'float'},
        s_fwidth_name: {'min': 1, 'max': 15, 'step': 0.1, 'type': 'float'}
    }
}

# Default values for fixed parameters
DEFAULT_VALUES = {
    'p_timecorr': 0.0,
    'aic_fmin': 1,
    'aic_fwidth': 0,
    'picker_aic_filter': 'ITAPER(1)>>BW_HP(3,2)'
}

# Mapping from SeisComP configuration parameter names to the template values
# (placeholders) used in the XML and station configuration templates.
CONFIG_PARAM_TEMPLATES = {
    'detecStream': '{ch}',
    'detecLocid': '{loc}',
    'trigOn': '{trig_on:.2f}',
    'trigOff': '1',
    'timeCorr': '{p_timecorr:.2f}',
    'picker.AIC.filter': '{picker_aic_filter}',
    'picker.AIC.minSNR': '{p_snr}',
    'detecFilter': 'RMHP(10)>>ITAPER(30)>>BW(4,{p_fmin},{p_fmax})>>STALTA({p_sta:.2f},{p_lta:.2f})',
    'spicker.AIC.filter': 'ITAPER(1)>>BW(4,{s_fmin},{s_fmax})',
    'spicker.AIC.step': '0.1',
    'spicker.AIC.minCnt': '3',
    'spicker.AIC.minSNR': '{s_snr:.2f}'
}

# CSV file headers
CSV_HEADERS = {
    'P': ['net.sta', p_sta_name, p_sta_width_name, p_fmin_name, p_fwidth_name,
          p_snr_name, trig_on_name, 'best_f1'],
    'S': ['net.sta', s_snr_name, s_fmin_name, s_fwidth_name, 'best_f1']
}

# Parameters to plot in optimization visualizations
PLOT_PARAMS = {
    'P': [p_sta_name, p_sta_width_name, p_fmin_name, p_fwidth_name, p_snr_name, trig_on_name],
    'S': [s_snr_name, s_fmin_name, s_fwidth_name]
}


def render_config_param_templates(params: dict) -> dict:
    """
    Build a dictionary with resolved template values for each SeisComP
    configuration parameter. Both the original parameter name (e.g.
    ``picker.AIC.filter``) and a sanitized key with dots replaced by underscores
    (e.g. ``picker_AIC_filter`` and a lower-case ``picker_aic_filter``) are
    provided so they can be used directly in ``str.format`` templates.
    Templates that cannot be rendered because placeholders are missing are
    skipped.
    """
    rendered = {}
    formatter = string.Formatter()

    for param_name, template in CONFIG_PARAM_TEMPLATES.items():
        required_fields = {
            field for _, field, _, _ in formatter.parse(template) if field
        }
        if not required_fields.issubset(params.keys()):
            continue

        value = template.format(**params)
        rendered[param_name] = value

        safe_key = param_name.replace('.', '_').replace('-', '_')
        for candidate in (safe_key, safe_key.lower()):
            rendered[candidate] = value

    return rendered
