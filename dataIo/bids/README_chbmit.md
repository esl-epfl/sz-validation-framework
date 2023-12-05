# README

This dataset is a BIDS compatible version of the CHB-MIT Scalp EEG Database. It reorganizes the file structure to comply with the BIDS specification. To this effect:

- The data from subject chb21 was moved to sub-01/ses-02.
- Metadata was organized according to BIDS.
- Data in the EEG edf files was modified to keep only the 18 channels from a double banana bipolar montage.
- Annotations were formatted as BIDS-score compatible `tsv` files.

## Details related to access to the data

### License

The dataset is released under the [Open Data Commons Attribution License v1.0](https://physionet.org/content/chbmit/view-license/1.0.0/).

### Contact person

The original Physionet CHB-MIT Scalp EEG Database was published by Ali Shoeb. This BIDS compatible version of the dataset was published by [Jonathan Dan](mailto:jonathan.dan@epfl.ch) - [ORCiD 0000-0002-2338-572X](https://orcid.org/0000-0002-2338-572X).

### Practical information to access the data

The original Physionet CHB-MIT Scalp EEG Database is available on the [Physionet website](https://physionet.org/content/chbmit/1.0.0/).

## Overview

### Project name

CHB-MIT Scalp EEG Database

### Year that the project ran

2010

### Brief overview of the tasks in the experiment

This database, collected at the Children’s Hospital Boston, consists of EEG recordings from pediatric subjects with intractable seizures. Subjects were monitored for up to several days following withdrawal of anti-seizure medication in order to characterize their seizures and assess their candidacy for surgical intervention.

### Description of the contents of the dataset

Each folder (sub-01, sub-01, etc.) contains between 9 and 42 continuous .edf files from a single subject. Hardware limitations resulted in gaps between consecutively-numbered .edf files, during which the signals were not recorded; in most cases, the gaps are 10 seconds or less, but occasionally there are much longer gaps. In order to protect the privacy of the subjects, all protected health information (PHI) in the original .edf files has been replaced with surrogate information in the files provided here. Dates in the original .edf files have been replaced by surrogate dates, but the time relationships between the individual files belonging to each case have been preserved. In most cases, the .edf files contain exactly one hour of digitized EEG signals, although those belonging to case sub-10 are two hours long, and those belonging to cases sub-04, sub-06, sub-07, sub-09, and sub-23 are four hours long; occasionally, files in which seizures are recorded are shorter.

The EEG is recorded at 256 Hz with a 16 bit resolution. The recordings are referenced in a double banana bipolar montage with 18 channels from the 10-20 electrode system.

The dataset also contains seizure annotations as start and stop times.

The dataset contains 664 `.edf` recordings. 129 those files that contain one or more seizures. In all, these records include 198 seizures.

## Methods

### Subjects

23 pediatric subjects with intractable seizures. (5 males, ages 3–22; and 17 females, ages 1.5–19; 1 n/a)

### Apparatus

Recordings were performed at the Children’s Hospital Boston using the International 10-20 system of EEG electrode positions. Signals were sampled at 256 samples per second with 16-bit resolution.