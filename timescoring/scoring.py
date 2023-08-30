''' Scoring functions between a reference annotation (ground-truth) and hypotheses (e.g. ML output).
'''

__author__ = "Jonathan Dan, Una Pale"
__email__ = "jonathan.dan at epfl.ch"

import numpy as np

from .annotations import Annotation


class _Scoring:
    """" Base class for different scoring methods. The class provides the common
    attributes and computation of common scores based on these attributes.
    """
    fs: int
    numSamples: int

    refTrue: int
    tp: int
    fp: int

    sensitivity: float
    precision: float
    f1: float
    fpRate: float

    def computeScores(self):
        """ Compute performance metrics."""
        # Sensitivity
        if self.refTrue > 0:
            self.sensitivity = self.tp / self.refTrue
        else:
            self.sensitivity = np.nan  # no ref event

        # Precision
        if self.tp + self.fp > 0:
            self.precision = self.tp / (self.tp + self.fp)
        else:
            self.precision = np.nan  # no hyp event

        # F1 Score
        if np.isnan(self.sensitivity) or np.isnan(self.precision):
            self.f1 = np.nan
        elif (self.sensitivity + self.precision) == 0:  # No overlap ref & hyp
            self.f1 = 0
        else:
            self.f1 = 2 * self.sensitivity * self.precision / (self.sensitivity + self.precision)

        # FP Rate
        self.fpRate = self.fp / (self.numSamples / self.fs / 3600 / 24)  # FP per day


class SampleScoring(_Scoring):
    """Calculates performance metrics on the sample by sample basis"""

    def __init__(self, ref: Annotation, hyp: Annotation, fs: int = 1):
        """Computes scores on a sample by sample basis.

        Args:
            ref (Annotation): Reference annotations (ground-truth)
            hyp (Annotation): Hypotheses annotations (output of a ML pipeline)
            fs (int): Sampling frequency of the labels. Default 1 Hz.
        """
        # Resample Data
        self.ref = Annotation(ref.events, fs, round(len(ref.mask) / ref.fs * fs))
        self.hyp = Annotation(hyp.events, fs, round(len(hyp.mask) / hyp.fs * fs))

        if len(self.ref.mask) != len(self.hyp.mask):
            raise ValueError(("The number of samples in the reference Annotation"
                              " (n={}) must match the number of samples in the "
                              "hypotheses Annotation (n={})").format(len(self.ref.mask), len(self.hyp.mask)))

        self.tpMask = self.ref.mask & self.hyp.mask
        self.fpMask = ~self.ref.mask & self.hyp.mask
        self.fnMask = self.ref.mask & ~self.hyp.mask

        self.fs = fs
        self.numSamples = len(self.ref.mask)

        self.refTrue = np.sum(self.ref.mask)

        self.tp = np.sum(self.tpMask)
        self.fp = np.sum(self.fpMask)

        self.computeScores()


class EventScoring(_Scoring):
    """Calculates performance metrics on an event basis"""
    class Parameters:
        """Parameters for event scoring"""

        def __init__(self, toleranceStart: float = 30,
                     toleranceEnd: float = 60,
                     minOverlap: float = 0,
                     maxEventDuration: float = 5 * 60,
                     minDurationBetweenEvents: float = 90):
            """Parameters for event scoring

            Args:
                toleranceStart (float): Allow some tolerance on the start of an event
                    without counting a false detection. Defaults to 30  # [seconds].
                toleranceEnd (float): Allow some tolerance on the end of an event
                    without counting a false detection. Defaults to 60  # [seconds].
                minOverlap (float): Minimum relative overlap between ref and hyp for
                    a detection. Defaults to 0 which corresponds to any overlap  # [relative].
                maxEventDuration (float): Automatically split events longer than a
                    given duration. Defaults to 5*60  # [seconds].
                minDurationBetweenEvents (float): Automatically merge events that are
                    separated by less than the given duration. Defaults to 90 # [seconds].
            """
            self.toleranceStart = toleranceStart
            self.toleranceEnd = toleranceEnd
            self.minOverlap = minOverlap
            self.maxEventDuration = maxEventDuration
            self.minDurationBetweenEvents = minDurationBetweenEvents

    def __init__(self, ref: Annotation, hyp: Annotation, param: Parameters = Parameters()):
        """Computes a scoring on an event basis.

        Args:
            ref (Annotation): Reference annotations (ground-truth)
            hyp (Annotation): Hypotheses annotations (output of a ML pipeline)
            param(EventScoring.Parameters, optional):  Parameters for event scoring.
                Defaults to default values.
        """
        # Resample data
        self.fs = ref.fs  # Operate at a time precision of 10 Hz
        self.ref = Annotation(ref.events, self.fs, round(len(ref.mask) / ref.fs * self.fs))
        self.hyp = Annotation(hyp.events, self.fs, round(len(hyp.mask) / hyp.fs * self.fs))

        # Merge events separated by less than param.minDurationBetweenEvents
        self.ref = EventScoring._mergeNeighbouringEvents(self.ref, param.minDurationBetweenEvents)
        self.hyp = EventScoring._mergeNeighbouringEvents(self.hyp, param.minDurationBetweenEvents)

        # Split long events to param.maxEventDuration
        self.ref = EventScoring._splitLongEvents(self.ref, param.maxEventDuration)
        self.hyp = EventScoring._splitLongEvents(self.hyp, param.maxEventDuration)

        self.numSamples = len(self.ref.mask)

        self.refTrue = len(self.ref.events)

        # Count True detections
        self.tp = 0
        self.tpMask = np.zeros_like(self.ref.mask)
        extendedRef = EventScoring._extendEvents(self.ref, param.toleranceStart, param.toleranceEnd)
        for event in extendedRef.events:
            relativeOverlap = (np.sum(self.hyp.mask[round(event[0] * self.fs):round(event[1] * self.fs)]) / self.fs
                               ) / (event[1] - event[0])
            if relativeOverlap > param.minOverlap + 1e-6:
                self.tp += 1
                self.tpMask[round(event[0] * self.fs):round(event[1] * self.fs)] = 1

        # Count False detections
        self.fp = 0
        for event in self.hyp.events:
            if np.any(~self.tpMask[round(event[0] * self.fs):round(event[1] * self.fs)]):
                self.fp += 1

        self.computeScores()

    def _splitLongEvents(events: Annotation, maxEventDuration: float) -> Annotation:
        """Split events longer than maxEventDuration in shorter events.
        Args:
            events (Annotation): Annotation object containing events to split
            maxEventDuration (float): maximum duration of an event [seconds]

        Returns:
            Annotation: Returns a new Annotation instance with all events split to
                a maximum duration of maxEventDuration.
        """

        shorterEvents = events.events.copy()

        for i, event in enumerate(shorterEvents):
            if event[1] - event[0] > maxEventDuration:
                shorterEvents[i] = (event[0], event[0] + maxEventDuration)
                shorterEvents.insert(i + 1, (event[0] + maxEventDuration, event[1]))

        return Annotation(shorterEvents, events.fs, len(events.mask))

    def _mergeNeighbouringEvents(events: Annotation, minDurationBetweenEvents: float) -> Annotation:
        """Merge events separated by less than longer than minDurationBetweenEvents.
        Args:
            events (Annotation): Annotation object containing events to split
            minDurationBetweenEvents (float): minimum duration between events [seconds]

        Returns:
            Annotation: Returns a new Annotation instance with events separated by less than
                minDurationBetweenEvents merged as one event.
        """

        mergedEvents = events.events.copy()

        i = 1
        while i < len(mergedEvents):
            event = mergedEvents[i]
            if event[0] - mergedEvents[i - 1][1] < minDurationBetweenEvents:
                mergedEvents[i - 1] = (mergedEvents[i - 1][0], event[1])
                del mergedEvents[i]
                i -= 1
            i += 1

        return Annotation(mergedEvents, events.fs, len(events.mask))

    def _extendEvents(events: Annotation, before: float, after: float) -> Annotation:
        """Extend duration of all events in an Annotation object.

        Args:
            events (Annotation): Annotation object containing events to extend
            before (float): Time to extend before each event [seconds]
            after (float):  Time to extend after each event [seconds]

        Returns:
            Annotation: Returns a new Annotation instance with all events extended
        """

        extendedEvents = events.events.copy()
        fileDuration = len(events.mask) / events.fs

        for i, event in enumerate(extendedEvents):
            extendedEvents[i] = (max(0, event[0] - before), (min(fileDuration, event[1] + after)))

        return Annotation(extendedEvents, events.fs, len(events.mask))
