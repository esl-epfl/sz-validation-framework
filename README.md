# Seizure validation Framework

This library provides script to work with the framework for the validation of EEG based automated seizure detection algorithms proposed [here](https://eslweb.epfl.ch/epilepsybenchmarks/framework-for-validation-of-epileptic-seizure-detection-algorithms/).

The library provides code to :

1. Convert EDF files from most open scalp EEG datasets of people with epilepsy to a standardized format
2. Convert seizure annotations from these datasets to a standardized format.
3. Evaluate the performance of seizure detection algorithm.

## Installation

Packages for the library will be provided once the code is stable. In the meantime, a list of dependencies are listed in [requirements.txt](https://github.com/esl-epfl/sz-validation-framework/blob/main/requirements.txt).

## Code

### Load EEG

`loadEeg/loadEdf.py` contains the code to load and convert EDF files from common scalp EEG datasets ([Physionet CHB-MIT](https://physionet.org/content/chbmit/1.0.0/), [Physionet Siena Scalp EEG](https://physionet.org/content/siena-scalp-eeg/1.0.0/), [TUH EEG Sz Corpus](https://isip.piconepress.com/projects/tuh_eeg), [SeizeIT1](https://rdr.kuleuven.be/dataset.xhtml?persistentId=doi:10.48804/P5Q0OJ)) to a standardized format.

The code can be used from the command line or as a python library. It can be used to :

- `loadEdf`: load data in memory as a `numpy.ndarray`
- `standardizeFile`: convert an EDF file to a standardized format
- `standardizeDataset`: standardize an entire dataset to a standardized format

#### Parameters

The following parameters are common to most functions. They all provide sane defaults.

- `electrodes` (`tuple[str]`, optional): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system. The constant `ELECTRODES` provides this tuple. The constant `BIPOLAR_DBANANA` provides the list of electrodes found in a double banana bipolar montage.
- `fs` (`int`, optional): sampling frequency. Defaults to 256.
- `inputMontage` (`Montage`, optional): montage of dataset to load. Default is monopolar. *(Physionet CHB-MIT is currently the only known dataset to only provide data in a bipolar montage)*
- `ref` (`str`, optional): reference electrode. Should be in the list of electrodes (for a monopolar montage) or the string                             `'bipolar-dBanana'` (for a double banana bipolar montage). Defaults to `'Cz'`.

#### Data Formats

The library allows to store the standardized data in one of the following formats:

- `EDF` (default)
- `csv`
- `csv.gzip`
- `parquet.gzip`

The output format is specified with the parameter `outFormat`

#### Data re-referencing

The library supports re-referencing from a monopolar montage to either a different reference electrode or to a double banana bipolar montage.

Bipolar data can currently not be re-referenced and is expected to be provided in a double banana montage.

#### Command line interface

The library also provides a command line interface :

```text
usage: EDF format standardization [-h] [-e ELECTRODES] [-f FS]
                                  [-m INPUTMONTAGE] [-r REF] [-o OUTFORMAT]
                                  input output

Converts EDF files in a montage to a standardized list of electrodes and
channel names. Two formats are allowed : either conversion of full datasets by
providing a directory name as input and conversion of individual files by
providing an edf file as input

positional arguments:
  input                 either the root directory of the original dataset or
                        the input edf file.
  output                either the root directory of the converted dataset or
                        the output filename. The data structure of the
                        original dataset is preserved.

options:
  -h, --help            show this help message and exit
  -e ELECTRODES, --electrodes ELECTRODES
                        List of electrodes. These should be provided as comma-
                        separated-values. By default uses the 19 electrodes of
                        the 10-20 system.
  -f FS, --fs FS        Sampling frequency for the converted data. Defaults to
                        256 Hz.
  -m INPUTMONTAGE, --inputMontage INPUTMONTAGE
                        Montage of the input, if uni(mono)polar - 'mono', if
                        bipolar - 'bipolar'. Defaults 'mono'
  -r REF, --ref REF     Reference for the converted data. Should be in the
                        list of electrodes (for a monopolar montage) or the
                        string 'bipolar-dBanana' (for a double banana bipolar
                        montage). Defaults to 'Cz'
  -o OUTFORMAT, --outFormat OUTFORMAT
                        Format of the output file. Should be one of 'edf',
                        'csv, 'csv.gzip', 'parquet.gzip'. Default is .edf
```
