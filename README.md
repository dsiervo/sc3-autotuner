# sc3-autotuner
Bayesian optimization approach for tuning SeisComP3's `scautopick` and `scanloc` modules.

Automatic parameter tuning for the SeisComP3 `scautopick` and `scanloc` modules using Bayesian optimization.

# Installation

## Requirements
* SeisComP
* SeisComP `scanloc` module
* Ubuntu 18.04 LTS or higher

1. Install the prerequisites for Python 3.8:

    ```bash
    $ sudo apt update
    $ sudo apt install software-properties-common
    ```

2. Install Python 3.8:

    ```bash
    $ sudo add-apt-repository ppa:deadsnakes/ppa
    $ sudo apt update
    $ sudo apt install python3.8 python3.8-dev python3.8-venv python3.8-tk
    ```

3. Download the sc3-autotuner repository:

    ```bash
    $ git clone https://github.com/dsiervo/sc3-autotuner
    $ cd sc3-autotuner
    ```

4. Create and activate a Python 3.8 virtual environment:

    ```bash
    $ python3.8 -m venv venv
    $ source venv/bin/activate
    ```

5. Update pip:

    ```bash
    (venv) $ pip install --upgrade pip
    ```

6. Install dependencies:
    Install headers and libraries for MySQL or MariaDB:
    ```bash
    (venv) $ sudo apt install default-libmysqlclient-dev
    ```
    Install Python dependencies:
    ```bash
    (venv) $ pip install -r requirements.txt
    ```

7. Add the S-AIC pick plugin to the `global.cfg` file of your SeisComP3 installation.

    Open the file **seicomp3/etc/global.cfg** and add *saic* to the end of the plugins list:

    ```bash
    plugins = hypo71,mlr,saic
    ```

8. Configure S-AIC as a secondary picker for `scautopick`:

    Open the file **seicomp3/etc/scautopick.cfg** (create it if it doesn’t exist) and add the following line (or replace the existing one):

    ```bash
    spicker = S-AIC
    ```

9. Deactivate the Python 3.8 environment and update the SeisComP3 configuration:

    ```bash
    (venv) $ deactivate
    $ seiscomp update-config
    ```

10. Add sc3-autotuner to your PATH in the **~/.bashrc** file:

    ```bash
    $ echo 'export PATH=<path to sc3-autotuner>:$PATH' >> ~/.bashrc
    $ source ~/.bashrc
    ```

11. Change the path to the sc3-autotuner folder in the first line of the **sc3autotuner.py** script.

# Usage
The program reads parameters from the `sc3-autotuner.inp` file located in the execution directory.

1. Copy the `sc3-autotuner.inp` file to your working directory.
2. Modify the `sc3-autotuner.inp` file according to your preferences.
3. Run the program:

    ```bash
    $ sc3autotuner.py
    ```

## sc3-autotuner.inp
You can add comments to the `sc3-autotuner.inp` file using the `#` character at the beginning of the line.

The following parameters are explained below:

### Global Parameters
**-** `tune_mode`: Controls whether to tune the picker (`picker`) or the associator (`asoc`). Currently, only `picker` is accepted.

**-** `debug`: If `True`, displays debugging information and plots the results.

**-** `deb_url`: IP address of the SQL server for querying picks and events.

**-** `ti`: Start time for querying picks and events. Must be in the `YYYY-MM-DD HH:MM:SS` format.

**-** `tf`: End time for querying picks and events. Must be in the `YYYY-MM-DD HH:MM:SS` format.

**-** `inv_xml`: Path to the XML file containing inventory information. You can use the SeisComP3 [scxmldump](https://docs.gempa.de/seiscomp3/current/apps/scxmldump.html) module to generate the file.

### Picker Mode Options
**-** `stations`: Comma-separated list of stations in the format `<network>.<station>.<location>.<channel without component>`. For example:

    stations = IU.ANMO.10.BH, CM.BAR2.00.HH, CM.DBB.20.EH

**-** `fdsn_ip`: IP address and port of the FDSN server for downloading waveforms (in SeisComP3, the FDSN server IP is usually the same as the SQL server IP with port 8091).

**-** `max_picks`: Maximum number of manual picks per station to use in tuning.

**-** `n_trials`: Number of attempts the program will make to tune the picker for each phase and station.

## Program Output
### Important Files
* Folder `output_station_files`: Contains the tuning results for each station in the appropriate format for incorporation into SeisComP3. To add these results to your system, copy these files to the `seicomp3/etc/key/scautopick` directory and add the following line to the corresponding files in the `seicomp3/etc/key/` path:

      scautopick

  SeisComP3 will now recognize these stations for use by the `scautopick` autopicker and use the parameters specified in the station configuration file in the `seicomp3/etc/key/scautopick` directory.

* Folder `images`: Contains interactive plots of the tuning process for each phase and station. These can be opened with any web browser.
* Files `results_P.csv` and `results_S.csv`: Compile the best parameters found for each phase and station along with the F1-score value for that iteration.

### Residual Files and Folders
* `exc_<station>_<phase>.xml`: Contains the picker parameters for the last iteration.
* `mseed_data`: Folder containing the waveforms used in the tuning process.
* `picks_xml`: Folder containing XML files in SeisComP3 format with the picks generated in the last iteration.
