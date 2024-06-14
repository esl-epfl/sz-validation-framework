from pathlib import Path

import numpy as np
import pandas as pd

from epilepsy2bids.annotations import Annotations, SeizureType
from timescoring import annotations, scoring

FS = 256


def toMask(annotations):
    mask = np.zeros(int(annotations.events[0]["recordingDuration"] * FS))
    for event in annotations.events:
        if event["eventType"].value != "bckg":
            mask[
                round(event["onset"] * FS) : round(event["onset"] + event["duration"])
                * FS
            ] = 1
    return mask


def computeScores(tp, fp, refTrue, duration):
    # Sensitivity
    if refTrue > 0:
        sensitivity = tp / refTrue
    else:
        sensitivity = np.nan  # no ref event

    # Precision
    if tp + fp > 0:
        precision = tp / (tp + fp)
    else:
        precision = np.nan  # no hyp event

    # F1 Score
    if np.isnan(sensitivity) or np.isnan(precision):
        f1 = np.nan
    elif (sensitivity + precision) == 0:  # No overlap ref & hyp
        f1 = 0
    else:
        f1 = 2 * sensitivity * precision / (sensitivity + precision)

    # FP Rate
    fpRate = fp / (duration / 3600 / 24)  # FP per day

    return sensitivity, precision, f1, fpRate


def evaluate(refFolder: str, hypFolder: str):
    DATASET = "tuh"
    results = {
        "dataset": [],
        "subject": [],
        "file": [],
        "duration": [],
        "tp_sample": [],
        "fp_sample": [],
        "refTrue_sample": [],
        "tp_event": [],
        "fp_event": [],
        "refTrue_event": [],
    }
    for refTsv in Path(refFolder).glob("sub-*/**/*.tsv"):
        ref = Annotations.loadTsv(refTsv)
        ref = annotations.Annotation(toMask(ref), FS)
        hypTsv = Path(hypFolder) / refTsv.relative_to(refFolder)
        if hypTsv.exists():
            hyp = Annotations.loadTsv(hypTsv)
            hyp = annotations.Annotation(toMask(hyp), FS)
        else:
            hyp = annotations.Annotation(np.zeros_like(ref.mask), ref.fs)

        sampleScore = scoring.SampleScoring(ref, hyp)
        eventScore = scoring.EventScoring(ref, hyp)

        results["dataset"].append(DATASET)
        results["subject"].append(refTsv.name.split("_")[0])
        results["file"].append(refTsv.name)
        results["duration"].append(len(ref.mask) / ref.fs)
        results["tp_sample"].append(sampleScore.tp)
        results["fp_sample"].append(sampleScore.fp)
        results["refTrue_sample"].append(sampleScore.refTrue)
        results["tp_event"].append(eventScore.tp)
        results["fp_event"].append(eventScore.fp)
        results["refTrue_event"].append(eventScore.refTrue)

    results = pd.DataFrame(results)

    results.to_csv("results.csv")

    # Sample results
    sensitivity, precision, f1, fpRate = computeScores(
        results["tp_sample"].sum(),
        results["fp_sample"].sum(),
        results["refTrue_sample"].sum(),
        results["duration"].sum(),
    )
    print(
        "# Sample scoring\n"
        + "- Sensitivity : {:.2f} \n".format(sensitivity)
        + "- Precision   : {:.2f} \n".format(precision)
        + "- F1-score    : {:.2f} \n".format(f1)
        + "- FP/24h      : {:.2f} \n".format(fpRate)
    )

    # Event results
    sensitivity, precision, f1, fpRate = computeScores(
        results["tp_event"].sum(),
        results["fp_event"].sum(),
        results["refTrue_event"].sum(),
        results["duration"].sum(),
    )
    print(
        "# Event scoring\n"
        + "- Sensitivity : {:.2f} \n".format(sensitivity)
        + "- Precision   : {:.2f} \n".format(precision)
        + "- F1-score    : {:.2f} \n".format(f1)
        + "- FP/24h      : {:.2f} \n".format(fpRate)
    )
