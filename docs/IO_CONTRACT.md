# sc3-autotuner I/O Contract

## Entrypoints
- `sc3autotuner.py` (CLI/script): reads `sc3-autotuner.inp` from the current
  working directory and runs picker tuning.

## Inputs
- `sc3-autotuner.inp` (required): runtime configuration.
- Inventory XML (`inv_xml` in the input file).
- SQL database (SeisComP schema) for picks and station coordinates.
- FDSN waveform servers (`fdsn_ip` list in the input file).
- SQL query templates in `utils/queries/`:
  - `picks_query.sql`
  - `coords_query.sql`
- Configuration templates in `bindings/`:
  - `config_template_P.xml`
  - `config_template.xml`
  - `station_NET_template`

## Outputs
- `results_P.csv`, `results_S.csv`: best parameters and `best_f1` per station.
- `images/`: Plotly HTML files for optimization history/slices/parallel coords.
- `output_station_files/station_<net>_<sta>`: station config output.
- `exc_<station>_<phase>.xml`: last-run XML config for scautopick.
- `mseed_data/<station>/`: downloaded waveform data.
- `picks_xml/`: generated pick XML files.
- `current_exc.txt`: execution context for `StaLta` (paths, inventory, debug).
- `stations_not_tuned.txt`: stations skipped with short reasons.

## Runtime Parameters (from `sc3-autotuner.inp`)
Key parameters consumed by the runtime:
- `tune_mode`, `debug`, `deb_url`, `ti`, `tf`, `inv_xml`
- `sql_usr`, `sql_psw`, optional `wf_url`, `wf_sql_usr`, `wf_sql_psw`
- `stations`, `fdsn_ip`, `max_picks`, `n_trials`, optional `radius`, `min_mag`
- optional `download_noise_p` (controls P-phase noise window downloads)
- optional `reference_picker_config`:
  - path to one `station_NET_STA` file, or
  - path to a directory containing `station_NET_STA` files.
  When provided, the runtime evaluates this reference config on the same
  waveforms used for Bayesian tuning and prints an overall per-phase
  comparison table (`F1`, `TPR`, `FPR`, confusion matrix) versus the best
  tuned result.

## Additional Outputs (when `reference_picker_config` is set)
- `reference_exc_xml/exc_reference_<sta>_<phase>.xml`: generated scautopick
  config XML used to score the reference station settings.
