from pathlib import Path

import numpy as np
import pyedflib

import epilepsy2bids.annotations
from epilepsy2bids.eeg import Eeg
import timescoring.annotations
import timescoring.scoring


def szDetection(edfFile: str, outFile: str):
    """Run a seizure detection algorithm on an EDF file.

    The algorithm implemented here provides random seizure annotations

    Args:
        edfFile (str): input EDF file
        outFile (str): output annotation file
    """
    # Load EEG
    print(edfFile)
    eeg = Eeg.loadEdf(edfFile)

    # Load metadata
    with pyedflib.EdfReader(edfFile) as edf:
        dateTime = edf.getStartdatetime()
        duration = edf.getFileDuration()
        edf._close()

    # Run algorithm
    output = np.random.rand(eeg.data.shape[1])
    output = np.convolve(output, np.ones(20 * int(eeg.fs)), "same") / (20 * eeg.fs)
    output = output > 0.5
    output = timescoring.annotations.Annotation(output, eeg.fs)
    output = timescoring.scoring.EventScoring._mergeNeighbouringEvents(output, 10)

    # Export results
    annotations = epilepsy2bids.annotations.Annotations()
    for event in output.events:
        annotation = epilepsy2bids.annotations.Annotation()
        annotation["onset"] = event[0]
        annotation["duration"] = event[1] - event[0]
        annotation["eventType"] = epilepsy2bids.annotations.SeizureType.sz
        annotation["confidence"] = "n/a"
        annotation["channels"] = "n/a"
        annotation["dateTime"] = dateTime
        annotation["recordingDuration"] = duration
        annotations.events.append(annotation)
    if len(output.events) == 0:
        annotation = epilepsy2bids.annotations.Annotation()
        annotation["onset"] = 0
        annotation["duration"] = duration
        annotation["eventType"] = epilepsy2bids.annotations.SeizureType.bckg
        annotation["confidence"] = "n/a"
        annotation["channels"] = "n/a"
        annotation["dateTime"] = dateTime
        annotation["recordingDuration"] = duration
        annotations.events.append(annotation)

    Path(outFile).parent.mkdir(parents=True, exist_ok=True)
    annotations.saveTsv(outFile)
