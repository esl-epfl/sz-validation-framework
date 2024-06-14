# Download datasets

To the best of our knowledge, there currently are four publicly available datasets of scalp EEG from people with epilepsy annotated by medical specialists that contain at least 10 subjects and at least 100 hours of recording.

 **Dataset**       | **# subjects** | **duration [h]** | **# seizures**
-------------------|----------------|------------------|----------------
 CHB-MIT           | 24             | 982              | 198
 Siena Scalp EEG   | 14             | 128              | 47
 TUH EEG Sz Corpus | 675            | 1476             | 4029
 SeizeIT1          | 42             | 4211             | 182

## Physionet CHB-MIT Scalp EEG Database

 The Physionet CHB-MIT Scalp EEG Database is freely available on the [Physionet website](https://doi.org/10.13026/C2K01R).

 The dataset is 42.6 GB. It can be downloaded directly from the [Physionet website](https://doi.org/10.13026/C2K01R):

- `wget -r -N -c -np https://physionet.org/files/chbmit/1.0.0/`

From Google Cloud Storage:

- `gsutil -m -u YOUR_PROJECT_ID cp -r gs://chbmit-1.0.0.physionet.org DESTINATION`

Or from AWS:

- `aws s3 sync s3://physionet-open/chbmit/1.0.0/ DESTINATION`

A pre-converted BIDS-compatible version is also available on [Zenodo](https://zenodo.org/records/10259996).

## Physionet Siena Scalp EEG Database

 The Physionet Siena Scalp EEG Database is freely available on the [Physionet website](https://doi.org/10.13026/s309-a395).

 The dataset is 20.3 GB. It can be downloaded directly from the [Physionet website](https://doi.org/10.13026/s309-a395):

- `wget -r -N -c -np https://physionet.org/files/siena-scalp-eeg/1.0.0/`

Or from AWS:

- `aws s3 sync s3://physionet-open/siena-scalp-eeg/1.0.0/ DESTINATION`

A pre-converted BIDS-compatible version is also available on [Zenodo](https://doi.org/10.5281/zenodo.10640762).

## TUH EEG Seizure Corpus

Access to the TUH EEG Seizure Corpus is managed by prof. Joseph Picone from Temple University. Information to request access to the dataset can be found on the [piconepress webpage](https://isip.piconepress.com/projects/nedc/html/tuh_eeg/).

## SeizeIT

The SeizeIT dataset is available upon request by contacting the data providers through the [KU Leuven Research Data Repository website](https://doi.org/10.48804/P5Q0OJ).

Downloading the dataset requires some scripts to query the available files and download them. A script to download the data is [available on github](https://gist.github.com/danjjl/c94c1ccd9aa0d77409805a11e79ea379).
