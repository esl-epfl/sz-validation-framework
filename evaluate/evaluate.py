import pandas as pd
import re
from timescoring import scoring
from timescoring.annotations import Annotation


def dfToEvents(df: pd.DataFrame) -> list[tuple[float, float]]:
    events = list()
    for _, row in df.sort_values(by=['startTime']).iterrows():
        if re.search(r'sz.*', row.event):
            events.append((row.startTime, row.endTime))
    return events


def evaluate(refFilename: str, hypFilename: str) -> pd.DataFrame:
    results = {
        'subject': [],
        'session': [],
        'recording': [],
        'dateTime': [],
        'duration': [],
        'numEvents': [],
        'sensitivity': [],
        'precision': [],
        'f1': [],
        'fpRate': [],
        'filepath': []
    }

    refDf = pd.read_csv(refFilename)
    hypDf = pd.read_csv(hypFilename)

    for filepath, _ in refDf.groupby(['filepath']):
        fs = 256
        nSamples = round(refDf[refDf.filepath == filepath[0]].duration.iloc[0] * fs)

        # Convert annotations
        ref = Annotation(dfToEvents(refDf[refDf.filepath == filepath[0]]), fs, nSamples)
        hyp = Annotation(dfToEvents(hypDf[hypDf.filepath == filepath[0]]), fs, nSamples)

        # Compute performance
        scores = scoring.EventScoring(ref, hyp)

        # Collect results
        for key in ['subject', 'session', 'recording', 'dateTime', 'duration', 'filepath']:
            results[key].append(refDf[refDf.filepath == filepath[0]][key].iloc[0])
        results['numEvents'].append(scores.refTrue)
        results['sensitivity'].append(scores.sensitivity)
        results['precision'].append(scores.precision)
        results['f1'].append(scores.f1)
        results['fpRate'].append(scores.fpRate)

    return pd.DataFrame(results)
