"""load annotations from the CHBMIT dataset https://physionet.org/content/chbmit/1.0.0/ to a Annotations object."""

import os
import re
import pyedflib

from dataIo.annotations import Annotation, Annotations, EventType, SeizureType


def _parseTimeStamp(string: str) -> float:
    """Parses timestamps from CHBMIT annotation files and returns a float representing the time from the earliest system time.

    Args:
        string (str): string to be parsed

    Returns:
        float: timestamp in seconds
    """
    timeStamp = re.findall(r"\d+", string)[-1]
    return float(timeStamp)


def _loadSeizures(edfFile: str, subject: str, edfFileName: str) -> list[tuple]:
    """Load seizures from a chb**-summary.txt file"""
    seizures = []
    summaryFile = os.path.join(
        os.path.dirname(edfFile), "{}-summary.txt".format(subject)
    )
    with open(summaryFile, "r") as summary:
        # Search for mention of edfFile in summary
        line = summary.readline()
        while line:
            if line == "File Name: {}\n".format(edfFileName):
                line = summary.readline()
                while ("File Name" not in line) and line:
                    if re.match(
                        "Seizure.*Start Time:", line
                    ):  # find start of new seizure
                        seizureStart = _parseTimeStamp(line)
                        seizureEnd = _parseTimeStamp(summary.readline())
                        seizures.append((seizureStart, seizureEnd))
                    line = summary.readline()
            else:
                line = summary.readline()
    return seizures


def loadAnnotationsFromEdf(edfFile: str) -> Annotations:
    """Loads annotations related to an EDF recording in the CHBMIT dataset.

    Args:
        edfFile (str): full path to the EDF for which annotations should be extracted.

    Returns:
        Annotations: an Annotations object
    """
    # Subject - Select folder name as subject name
    subject = os.path.basename(os.path.dirname(edfFile))

    # dateTime and duration
    with pyedflib.EdfReader(edfFile) as edf:
        dateTime = edf.getStartdatetime()
        duration = edf.getFileDuration()
        edf._close()

    # Get Seizure type
    seizureType = SeizureType.sz  # seizure types are not available for CHB-MIT

    # Load Seizures
    seizures = _loadSeizures(edfFile, subject, os.path.basename(edfFile))

    # Confidence
    confidence = "n/a"  # confidence is not available for CHB-MIT

    # Channels
    channels = "n/a"  # channels are not available for CHB-MIT

    # Populate dictionary
    if len(seizures) == 0:
        seizureType = EventType.bckg
        seizures.append((0, duration))

    annotations = Annotations()
    for seizure in seizures:
        annotation = Annotation()
        annotation["onset"] = seizure[0]
        annotation["duration"] = seizure[1] - seizure[0]
        annotation["eventType"] = seizureType
        annotation["confidence"] = confidence
        annotation["channels"] = channels
        annotation["dateTime"] = dateTime
        annotation["recordingDuration"] = duration
        annotations.events.append(annotation)

    return annotations
