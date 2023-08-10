"""Script to load annotations from the CHBMIT dataset https://physionet.org/content/chbmit/1.0.0/
to the standardized annotation format.

The annotation format is described in more detail on
https://eslweb.epfl.ch/epilepsybenchmarks/framework-for-validation-of-epileptic-seizure-detection-algorithms/#annotation

The script can be used as a library or as a command line application.
"""

import argparse
import glob
import os
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pyedflib


def _parseTimeStamp(string: str) -> float:
    """Parses timestamps from CHBMIT annotation files and returns a float representing the time from the earliest system time.

    Args:
        string (str): string to be parsed

    Returns:
        float: timestamp in seconds
    """
    timeStamp = re.findall(r'\d+', string)[-1]
    return float(timeStamp)


def _loadSeizures(edfFile: str, subject: str, edfFileName: str) -> list[tuple]:
    """Load seizures from a chb**-summary.txt file"""
    seizures = []
    summaryFile = os.path.join(os.path.dirname(edfFile), '{}-summary.txt'.format(subject))
    with open(summaryFile, 'r') as summary:
        # Search for mention of edfFile in summary
        line = summary.readline()
        while line:
            if line == 'File Name: {}\n'.format(edfFileName):
                line = summary.readline()
                while ('File Name' not in line) and line:
                    if re.match('Seizure.*Start Time:', line):  # find start of new seizure
                        seizureStart = _parseTimeStamp(line)
                        seizureEnd = _parseTimeStamp(summary.readline())
                        seizures.append((seizureStart, seizureEnd))
                    line = summary.readline()
            else:
                line = summary.readline()
    return seizures


def convertAnnotationsEdf(rootDir: str, edfFile: str, outFile: str = None) -> pd.DataFrame:
    """Loads annotations related to an EDF recording in the CHBMIT dataset. The annotations are returned as a pandas DataFrame
        and optionally written to a csv file.

    Args:
        rootDir (str): root directory of the CHBMIT dataset. This refers to the location containing the file SUBJECT-INFO
            and the folders for each subject.
        edfFile (str): full path to the EDF for which annotations should be extracted.
        outFile (str, optional): full path to the csv file to which the annotations will be written. If it is set to None no
            annotations will be written. Defaults to None.

    Raises:
        ValueError: raised if the seizure type is unknown in the SUBJECT-INFO file.
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

    # Correct typos in filenames - in case name in .txt file is different from .edf file
    correctedEdfFileName = os.path.basename(edfFile)

    # Subject - Select folder name as subject name
    subject = edfFile.split('/')[-2]

    # Session - All recordings belong to the same session because recorded in a row without removing EEG cap
    session = 1  # TODO check if two consecutive files are more than e.g. 1h apart - then start new session

    # Recording - Read last part in .edf file name
    fileName = Path(edfFile).stem
    recording = fileName.split('_')
    if len(recording) == 0:
        recording = 1
    else:
        recording = recording[-1]

    # dateTime and duration
    with pyedflib.EdfReader(edfFile) as edf:
        dateTime = edf.getStartdatetime()
        duration = edf.getFileDuration()
        edf._close()

    # Get Seizure type
    seizureType = 'sz'  # seizure types are note specified for CHBMIT dabase

    # Load Seizures
    seizures = _loadSeizures(edfFile, subject, correctedEdfFileName)

    # Confidence
    confidence = 1

    # Channels
    channels = 'all'  # channels are not specified for CHBMIT database

    # Filepath
    filepath = subject + '/' + os.path.basename(edfFile)

    # Populate dictionary
    if len(seizures) == 0:
        seizureType = 'bckg'
        seizures.append((0, duration))

    for seizure in seizures:
        annotations['subject'].append(subject)
        annotations['session'].append(session)
        annotations['recording'].append(recording)
        annotations['dateTime'].append(dateTime)
        annotations['duration'].append(duration)
        annotations['event'].append(seizureType)
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
    """Loads annotations related to a subject in the CHBMIT dataset. The annotations are returned as a pandas DataFrame
        and optionally written to a csv file.

    Args:
        rootDir (str): root directory of the CHBMIT dataset. This refers to the location containing the file SUBJECT-INFO
            and the folders for each subject.
        subject (str): name of the subject in the CHBMIT dataset (e.g. chb01)
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

    edfFiles = np.sort(glob.glob(os.path.join(rootDir, subject, '*.edf')))
    for edfFile in edfFiles:
        print(edfFile)
        edfAnnotations = convertAnnotationsEdf(rootDir, edfFile)
        annotationDf = pd.concat([annotationDf, edfAnnotations])

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


def convertAllAnnotations(rootDir: str, outFile: str = None) -> pd.DataFrame:
    """Loads all annotations in the CHBMIT dataset. The annotations are returned as a pandas DataFrame and optionally written
        to a csv file.

    Args:
        rootDir (str): root directory of the CHBMIT dataset. This refers to the location containing the file SUBJECT-INFO
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

    edfFiles = np.sort(glob.glob(os.path.join(rootDir, '*/*.edf')))
    for edfFile in edfFiles:
        print(edfFile)
        edfAnnotations = convertAnnotationsEdf(rootDir, edfFile)
        annotationDf = pd.concat([annotationDf, edfAnnotations])

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='CHBMIT Annotation converter',
        description='Converts annatations from the CHBMIT dataset to a standardized format',
    )
    parser.add_argument('rootDir',
                        help="root directory of the CHBMIT dataset. This refers to the location containing the file "
                             "SUBJECT-INFO and the folders for each subject.")
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
