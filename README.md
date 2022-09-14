# sc3-autotuner
Bayesian optimization approach for tuning SeisComP3's scautopick and scanloc modules.

Ajuste automático de parámetros de los módulos de SeisComP3 scautopick y scanloc usando optimización bayesiana.

# Instalación

## Requisitos
* SeisComP3
* Módulo scanloc de SeisComP3
* Ubuntu 18.04 LTS o superior

1. Instale los pre requisitos de python3.8:

    ```bash
    $ sudo apt update
    $ sudo apt install software-properties-common
    ```

2. Instale python3.8:

    ```bash
    $ sudo add-apt-repository ppa:deadsnakes/ppa
    $ sudo apt update
    $ sudo apt install python3.8 python3.8-dev python3.8-venv python3.8-tk
    ```

3. Descargue el repositorio de sc3-autotuner:

    ```bash
    $ git clone https://github.com/dsiervo/sc3-autotuner
    $ cd sc3-autotuner
    ```

4. Cree y active una instancia de python3.8:

    ```bash
    $ python3.8 -m venv venv
    $ source venv/bin/activate
    ```

5. Actualice pip:

    ```bash
    (venv) $ pip install --upgrade pip
    ```

6. Instale las dependencias:
    ```bash
    (venv) $ pip install -r requirements.txt
    ```

7. Agregue el pluging del pick S-AIC al global.cfg de su instalación de SeisComP3.

    Abra el archivo **seicomp3/etc/global.cfg** y agregue *saic* al final de la lista de plugins:

    ```bash
    plugins = hypo71,mlr,saic
    ```

8. Configure el S-AIC como picker secundario del scautopick:

    Abra el archivo **seicomp3/etc/scautopick.cfg** (si no existe creelo en esa ruta) y agregue la siguiente línea (o reemplace la existente):

    ```bash
    spicker = S-AIC
    ```

9. Desactive el ambiente de python3.8 y actualice la configuración de SeisComP3:

    ```bash
    (venv) $ deactivate
    $ seiscomp update-config
    ```

10. Agregue sc3-autotuner al path en el archivo **~/.bashrc**:

    ```bash
    $ echo 'export PATH=<ruta a sc3-autotuner>:$PATH' >> ~/.bashrc
    $ source ~/.bashrc
    ```

# Uso
El programa lee los parámetros desde el archivo sc3-autotuner.inp que se encuentran en el directorio de ejecución.

1. Copie en su directorio de trabajo el archivo *sc3-autotuner.inp*. 
2. Modifique el archivo *sc3-autotuner.inp* de acuerdo a sus preferencias.
3. Ejecute el programa:

    ```bash
    $ sc3autotuner.py
    ```

## sc3-autotuner.inp
Puede introducir comentarios al *sc3-autotuner.inp* usando el caracter # al inicio de la línea.

A continuación se explicará cada uno de estos parámetros:

### Parámetros Globales
**-** `tune_mode`: Controla si se ajusta el picker (`picker`) o se ajusta el asociador (`asoc`). Por el momento sólo se acepta el valor `picker`.

**-** `debug`: Si es `True` muestra información de depuración y mostrará plots de los resultados.

**-** `deb_url`: Dirección IP del servidor SQL para la consulta de picks y eventos.

**-** `ti`: Tiempo inicial para la consulta de picks y eventos. Debe ser una fecha en formato `YYYY-MM-DD HH:MM:SS`.

**-** `tf`: Tiempo final para la consulta de picks y eventos. Debe ser una fecha en formato `YYYY-MM-DD HH:MM:SS`.

**-** `inv_xml`: Ruta al archivo XML de con la información del inventory. Puede usar el módulo de SeisComP3 [scxmldump](https://docs.gempa.de/seiscomp3/current/apps/scxmldump.html) para generar el archivo.


### Opciones del modo picker
**-** `stations`: Lista de estaciones a usar separadas por coma en formato: `<network>.<station>.<location>.<channel sin componente>`. Por ejemplo:

    stations = IU.ANMO.10.BH, CM.BAR2.00.HH, CM.DBB.20.EH

**-** `fdsn_ip`: Dirección IP y puerto del servidor FDSN para la descarga de las formas de onda (Usualmente en SeisComP3 la IP del servidor FDSN es la misma que la IP del servidor SQL mas el puerto 8091).

**-** `max_picks`: Número máximo de picks manuales por estación a usar en el ajuste.

**-** `n_trials`: Número de intentos que hará el programa para ajustar el picker de cada fase y de cada estación.

## Salida del programa
### Archivos importantes
* Carpeta `output_station_files`: Los archivos contenidos en esta carpeta contienen los resultados del ajuste de cada estación en el formato apropiado para su incorporación en la configuración de SeisComP3. Para agregar estos resultados a su sistema debe copiar estos archivos al directorio `seicomp3/etc/key/scautopick` y luego agregar la siguiente línea en los archivos homónimos en la ruta `seicomp3/etc/key/`:

      scautopick

  Ahora SeisComP3 reconocerá que dichas estaciones están disponibles para ser usadas por el autopicker scautopick y para el picado utilizará los parámetros consignados en el archivo de configuración de la estación en la ruta `seicomp3/etc/key/scautopick`.

* Carpeta `images`: Gráficas interactivas del proceso de ajuste de cada fase de cada estación. Puede abrirlas con cualquier navegador web.
* Archivos `results_P.csv` y `results_S.csv`: Compilación de los mejores parámetros encontrados para cada fase y estación junto con el valor del f1-score de esa iteración.

### Archivos y carpetas residuales
* `exc_<station>_<phase>.xml`: Contienen los parámetros de los pickers en la última iteración.
* `mseed_data`: Carpeta con las formas de onda usadas en el ajuste.
* `picks_xml`: Carpeta con archivos XML en formato seiscomp con los picks generados en la última iteración. 
