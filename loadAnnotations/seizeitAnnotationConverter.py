"""Script to load annotations from the SeizeIT dataset https://doi.org/10.48804/P5Q0OJ
to the standardized annotation format.

The annotation format is described in more detail on
https://eslweb.epfl.ch/epilepsybenchmarks/framework-for-validation-of-epileptic-seizure-detection-algorithms/#annotation

The script can be used as a library or as a command line application.
"""

import argparse
import glob
import os
from pathlib import Path

import pandas as pd
import pyedflib


def _loadSeizures(tsvFile: str) -> tuple:
    """Load seizures from a SeizeIT P_IDXX_rx_a2.tsv file"""
    seizures = []
    types = []
    annotations = pd.read_csv(tsvFile, comment="#", delimiter='\t', names=['start', 'stop', 'type', 'comments'])
    for _, row in annotations.iterrows():
        seizures.append((row['start'], row['stop']))

        seizureType = row['type']
        if seizureType == 'FIA':
            seizureType = 'sz-foc-ia'
        elif seizureType == 'FA':
            seizureType = 'sz-foc-a'
        elif seizureType == 'F-BTC':
            seizureType = 'sz-foc-ua-f2b'
        else:
            raise ValueError("Unknown seizure type for SeizeIT dataset: {}.".format(seizureType))
        types.append(seizureType)

    return seizures, types


def convertAnnotationsEdf(rootDir: str, edfFile: str, outFile: str = None) -> pd.DataFrame:
    """Loads annotations related to an EDF recording in the dataset. The annotations are returned as a pandas DataFrame
        and optionally written to a csv file.

    Args:
        rootDir (str): root directory of the dataset. This refers to the location containing the file subject_info.csv
            and the folders for each subject.
        edfFile (str): full path to the EDF for which annotations should be extracted.
        outFile (str, optional): full path to the csv file to which the annotations will be written. If it is set to None no
            annotations will be written. Defaults to None.

    Raises:
        ValueError: raised if the seizure type is unknown in the subject_info.csv file.
        ValueError: raised if the format of an annotation is unknown.

    Returns:
        pd.DataFrame: DataFrame containing the annotations for each seizure the following fields are give : subject, session,
            recording, recording start dateTime, recording duration, seizure type, event start time in seconds relative to the
            start of the recording, event end time [s], confidence=1, channels, filepath
    """

    annotations = {
        'subject': [],
        'session': [],
        'recording': [],
        'dateTime': [],
        'duration': [],
        'event': [],
        'startTime': [],
        'endTime': [],
        'confidence': [],
        'channels': [],
        'filepath': []
    }

    # Subject
    subject = edfFile.split('/')[-2]

    # Session
    fileName = Path(edfFile).stem
    session = 1
    # Recording
    recording = fileName.split('_')[-1]

    # dateTime and duration
    with pyedflib.EdfReader(edfFile) as edf:
        dateTime = edf.getStartdatetime()
        duration = edf.getFileDuration()
        edf._close()

    # Load Seizures and types
    annotationTsv = edfFile[:-4] + '_a2.tsv'
    seizures, types = _loadSeizures(annotationTsv)

    # Confidence
    confidence = 1

    # Channels
    channels = 'all'  # TODO use lateralization info to populate channels

    # Filepath
    filepath = subject + '/' + os.path.basename(edfFile)

    # Populate dictionary
    if len(seizures) == 0:
        types = ['bckg']
        seizures.append((0, duration))

    for i, seizure in enumerate(seizures):
        annotations['subject'].append(subject)
        annotations['session'].append(session)
        annotations['recording'].append(recording)
        annotations['dateTime'].append(dateTime)
        annotations['duration'].append(duration)
        annotations['event'].append(types[i])
        annotations['startTime'].append(int(seizure[0]))
        annotations['endTime'].append(int(seizure[1]))
        annotations['confidence'].append(confidence)
        annotations['channels'].append(channels)
        annotations['filepath'].append(filepath)

    annotationDf = pd.DataFrame(annotations)

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


def convertAnnotationsSubject(rootDir: str, subject: str, outFile: str = None) -> pd.DataFrame:
    """Loads annotations related to a subject in the dataset. The annotations are returned as a pandas DataFrame
        and optionally written to a csv file.

    Args:
        rootDir (str): root directory of the dataset. This refers to the location containing the file subject_info.csv
            and the folders for each subject.
        subject (str): name of the subject in the dataset (e.g. P_ID10)
        outFile (str, optional): full path to the csv file to which the annotations will be written. If it is set to None no
            annotations will be written. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing the annotations for each seizure the following fields are give : subject, session,
            recording, recording start dateTime, recording duration, seizure type, event start time in seconds relative to the
            start of the recording, event end time [s], confidence=1, channels, filepath
    """
    annotations = {
        'subject': [],
        'session': [],
        'recording': [],
        'dateTime': [],
        'duration': [],
        'event': [],
        'startTime': [],
        'endTime': [],
        'confidence': [],
        'channels': [],
        'filepath': []
    }
    annotationDf = pd.DataFrame(annotations)

    edfFiles = glob.iglob(os.path.join(rootDir, subject, '*.edf'))
    for edfFile in edfFiles:
        edfAnnotations = convertAnnotationsEdf(rootDir, edfFile)
        annotationDf = pd.concat([annotationDf, edfAnnotations])

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


def convertAllAnnotations(rootDir: str, outFile: str = None) -> pd.DataFrame:
    """Loads all annotations in the dataset. The annotations are returned as a pandas DataFrame and optionally written
        to a csv file.

    Args:
        rootDir (str): root directory of the dataset. This refers to the location containing the file subject_info.csv
            and the folders for each subject.
        outFile (str, optional): full path to the csv file to which the annotations will be written. If it is set to None no
            annotations will be written. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing the annotations for each seizure the following fields are give : subject, session,
            recording, recording start dateTime, recording duration, seizure type, event start time in seconds relative to the
            start of the recording, event end time [s], confidence=1, channels, filepath
    """
    annotations = {
        'subject': [],
        'session': [],
        'recording': [],
        'dateTime': [],
        'duration': [],
        'event': [],
        'startTime': [],
        'endTime': [],
        'confidence': [],
        'channels': [],
        'filepath': []
    }
    annotationDf = pd.DataFrame(annotations)

    edfFiles = glob.iglob(os.path.join(rootDir, '*/*.edf'))
    for edfFile in edfFiles:
        edfAnnotations = convertAnnotationsEdf(rootDir, edfFile)
        annotationDf = pd.concat([annotationDf, edfAnnotations])

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='SeizeIT Annotation converter',
        description='Converts annatations from the SeizeIT dataset to a standardized format',
    )
    parser.add_argument('rootDir',
                        help="root directory of the SeizeIT dataset. This refers to the location containing the file "
                             "subject_info.csv and the folders for each subject.")
    parser.add_argument('outFile',
                        help="full path to the csv file to which the annotations will be written.")
    parser.add_argument('-s', '--subject',
                        help="If provided, only extracts the annotations from the subject.")
    parser.add_argument('-e', '--edf',
                        help="If provided, only extracts the annotations from the specified EDF file. Expects a full path.")
    args = parser.parse_args()

    if args.edf is not None:
        convertAnnotationsEdf(args.rootDir, args.edf, args.outFile)
    elif args.subject is not None:
        convertAnnotationsSubject(args.rootDir, args.subject, args.outFile)
    else:
        convertAllAnnotations(args.rootDir, args.outFile)
