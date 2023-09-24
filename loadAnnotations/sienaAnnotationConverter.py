"""Script to load annotations from the Siena dataset https://doi.org/10.13026/5d4a-j060
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
import time

import pandas as pd
import pyedflib
import numpy as np

def _parseTimeStamp(string: str) -> float:
    """Parses timestamps from Siena annotation files and returns a float representing the time from the earliest system time.

    Accepts the following formats with any random string before the timestamp :
    - 'Registration start time: 19.00.44'
    - 'Start time: 21:51:02'

    Args:
        string (str): string to be parsed as a timestamp

    Returns:
        float: timestamp in seconds from the earliest system time
    """
    timeStamp = re.findall('.*[ |:]([0-9]+.[0-9]+.[0-9]+).*', string)[0]
    return time.mktime(time.strptime(timeStamp.replace(':', '.'), "%H.%M.%S"))


def _substractTimeStamps(time1: float, time2: float) -> float:
    """Substract to timestamps in seconds"""
    difference = time1 - time2
    if difference < 0:
        difference += 24 * 60 * 60  # Correct for day shift
    return difference


def _loadSeizures(edfFile: str, subject: str, correctedEdfFileName: str) -> list[tuple]:
    """Load seizures from a Siena Seizures-list-Pxx.txt file"""
    seizures = []
    summaryFile = os.path.join(os.path.dirname(edfFile), 'Seizures-list-{}.txt'.format(subject))
    with open(summaryFile, 'r') as summary:
        # Search for mention of edfFile in summary
        line = summary.readline()
        while line:
            if re.search(r'File name: {} *\n'.format(correctedEdfFileName), line):
                firstLine = summary.readline()
                # PN01 exception
                if correctedEdfFileName == 'PN01.edf':
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    _ = summary.readline()
                    for _ in range(2):
                        _ = summary.readline()
                        start = _parseTimeStamp(summary.readline())
                        end = _parseTimeStamp(summary.readline())
                        _ = summary.readline()
                        seizures.append((_substractTimeStamps(start, registrationStart),
                                        (_substractTimeStamps(end, registrationStart))))
                elif correctedEdfFileName == 'PN00-3.edf': #seizure last 1hour
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    start = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp('Seizure end time: 18.29.29\n')  #correct time
                    seizures.append((_substractTimeStamps(start, registrationStart),
                                     (_substractTimeStamps(end, registrationStart))))
                elif correctedEdfFileName == 'PN10-7.8.9.edf': #seizure last 1hour
                    if (firstLine== 'Registration start time:1 6.49.25\n'): #extra space
                        firstLine='Registration start time:16.49.25\n'
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    start = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp(summary.readline())
                    seizures.append((_substractTimeStamps(start, registrationStart),
                                     (_substractTimeStamps(end, registrationStart))))
                # PN12 exception
                elif 'Seizure start time: ' in firstLine:
                    start = _parseTimeStamp(firstLine)
                    end = _parseTimeStamp(summary.readline())
                    seizures.append((_substractTimeStamps(start, registrationStart),
                                    (_substractTimeStamps(end, registrationStart))))
                # Standard format
                elif 'Registration start time:' in firstLine:
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    start = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp(summary.readline())
                    seizures.append((_substractTimeStamps(start, registrationStart),
                                    (_substractTimeStamps(end, registrationStart))))
                else:
                    raise ValueError("Unknown format for Siena summary file.")
            line = summary.readline()
    return seizures


def _correctEdfFileNameTypos(filename: str) -> str:
    """Correct typos in filenames in .txt file when compared to .edf files"""
    correctedEdfFileName = os.path.basename(filename)
    if correctedEdfFileName == 'PN01-1.edf':
        correctedEdfFileName = 'PN01.edf'
    elif correctedEdfFileName == 'PN06-1.edf':
        correctedEdfFileName = 'PNO6-1.edf'  # big o instead of 0
    elif correctedEdfFileName == 'PN06-2.edf':
        correctedEdfFileName = 'PNO6-2.edf'  # big o instead of 0
    elif correctedEdfFileName == 'PN06-4.edf':
        correctedEdfFileName = 'PNO6-4.edf'  # big o instead of 0
    elif correctedEdfFileName == 'PN11-1.edf':
        correctedEdfFileName = 'PN11-.edf'
    return correctedEdfFileName


def convertAnnotationsEdf(rootDir: str, edfFile: str, outFile: str = None) -> pd.DataFrame:
    """Loads annotations related to an EDF recording in the Siena dataset. The annotations are returned as a pandas DataFrame
        and optionally written to a csv file.

    Args:
        rootDir (str): root directory of the Siena dataset. This refers to the location containing the file subject_info.csv
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

    subject_info = pd.read_csv(os.path.join(rootDir, 'subject_info.csv'))

    # Correct typos in filenames in .txt file when compared to .edf files
    correctedEdfFileName = _correctEdfFileNameTypos(edfFile)

    # Subject
    subject = edfFile.split('/')[-2]

    # Session
    fileName = Path(edfFile).stem
    session = fileName.split('-')
    if len(session) == 0:
        session = 1
    else:
        session = session[-1]

    # Recording
    recording = 1

    # dateTime and duration
    with pyedflib.EdfReader(edfFile) as edf:
        dateTime = edf.getStartdatetime()
        duration = edf.getFileDuration()
        edf._close()

    # Get Seizure type
    seizureType = subject_info[subject_info.patient_id == subject][' seizure'].iloc[0]
    if seizureType == 'IAS':
        seizureType = 'sz-foc-ia'
    elif seizureType == 'WIAS':
        seizureType = 'sz-foc-ia'
    elif seizureType == 'FBTC':
        seizureType = 'sz-foc-ua-f2b'
    else:
        raise ValueError("Unknown seizure type for Siena dataset.")

    # Load Seizures
    seizures = _loadSeizures(edfFile, subject, correctedEdfFileName)

    # Confidence
    confidence = 1

    # Channels
    channels = 'all'  # TODO use lateralization info to populate channels

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

        if (int(seizure[1])>duration): #end of seizure after end of the file
            print('ERROR: end of seizure after end of the file: ', filepath)

    annotationDf = pd.DataFrame(annotations)

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


def convertAnnotationsSubject(rootDir: str, subject: str, outFile: str = None) -> pd.DataFrame:
    """Loads annotations related to a subject in the Siena dataset. The annotations are returned as a pandas DataFrame
        and optionally written to a csv file.

    Args:
        rootDir (str): root directory of the Siena dataset. This refers to the location containing the file subject_info.csv
            and the folders for each subject.
        subject (str): name of the subject in the Siena dataset (e.g. PN00)
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

    # edfFiles = glob.iglob(os.path.join(rootDir, subject, '*.edf'))
    edfFiles = np.sort(glob.glob(os.path.join(rootDir, subject, '*.edf'))) #sort them
    for edfFile in edfFiles:
        edfAnnotations = convertAnnotationsEdf(rootDir, edfFile)
        annotationDf = pd.concat([annotationDf, edfAnnotations])

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


def convertAllAnnotations(rootDir: str, outFile: str = None) -> pd.DataFrame:
    """Loads all annotations in the Siena dataset. The annotations are returned as a pandas DataFrame and optionally written
        to a csv file.

    Args:
        rootDir (str): root directory of the Siena dataset. This refers to the location containing the file subject_info.csv
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

    # edfFiles = glob.iglob(os.path.join(rootDir, '*/*.edf'))
    edfFiles = np.sort(glob.glob(os.path.join(rootDir, '*/*.edf'))) #sort them
    for edfFile in edfFiles:
        edfAnnotations = convertAnnotationsEdf(rootDir, edfFile)
        annotationDf = pd.concat([annotationDf, edfAnnotations])

    if outFile is not None:
        annotationDf.sort_values(by=['filepath']).to_csv(outFile, index=False)

    return annotationDf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Siena Annotation converter',
        description='Converts annatations from the Siena dataset to a standardized format',
    )
    parser.add_argument('rootDir',
                        help="root directory of the Siena dataset. This refers to the location containing the file "
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
