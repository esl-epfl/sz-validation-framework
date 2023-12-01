from datetime import datetime
import enum
from typing import TypedDict

import numpy as np


# ILAE Seizure classification
_SZ_TYPES = {
    "sz": {
        "foc": {
            "a": {
                "m": (
                    "automatisms",
                    "atonic",
                    "clonic",
                    "spasms",
                    "hyperkinetic",
                    "myoclonic",
                    "tonic",
                ),
                "nm": ("automatic", "behavior", "cognitive", "emotional", "sensory"),
                "f2b": (),
                "um": (),
            },
            "ia": {
                "m": (
                    "automatisms",
                    "atonic",
                    "clonic",
                    "spasms",
                    "hyperkinetic",
                    "myoclonic",
                    "tonic",
                ),
                "nm": ("automatic", "behavior", "cognitive", "emotional", "sensory"),
                "f2b": (),
                "um": (),
            },
            "ua": {
                "m": (
                    "automatisms",
                    "atonic",
                    "clonic",
                    "spasms",
                    "hyperkinetic",
                    "myoclonic",
                    "tonic",
                ),
                "nm": ("automatic", "behavior", "cognitive", "emotional", "sensory"),
                "f2b": (),
                "um": (),
            },
        },
        "gen": {
            "m": (
                "tonicClonic",
                "clonic",
                "tonic",
                "myoTC",
                "myoAtonic",
                "atonic",
                "spasms",
            ),
            "nm": ("automatic", "behavior", "cognitive", "emotional", "sensory"),
            "um": (),
        },
        "uo": {"m": ("tonicClonic", "spasms"), "nm": ["behavior"], "um": ()},
    }
}
SZ_TYPES = dict()
for sz, focDict in _SZ_TYPES.items():
    SZ_TYPES[sz] = sz
    for focus, subDict in focDict.items():
        label = "_".join((sz, focus))
        if focus == "foc":
            awareDict = subDict
            for awareness, motorDict in awareDict.items():
                label = "_".join((sz, focus, awareness))
                SZ_TYPES[label] = label
                for motor, clinics in motorDict.items():
                    label = "_".join((sz, focus, awareness, motor))
                    SZ_TYPES[label] = label
                    for clinic in clinics:
                        label = "_".join((sz, focus, awareness, motor, clinic))
                        SZ_TYPES[label] = label
        else:
            motorDict = subDict
            for motor, clinics in motorDict.items():
                label = "_".join((sz, focus, motor))
                SZ_TYPES[label] = label
                for clinic in clinics:
                    label = "_".join((sz, focus, motor, clinic))
                    SZ_TYPES[label] = label
SeizureType = enum.Enum("SeizureType", SZ_TYPES)

EVENT_TYPES = SZ_TYPES.copy()
EVENT_TYPES["bckg"] = "bckg"
EventType = enum.Enum("EventType", EVENT_TYPES)


class Annotation(TypedDict):
    onset: float  # start time of the event from the beginning of the recording, in seconds
    duration: float  # duration of the event, in seconds
    eventType: EventType  # type of the event
    confidence: float  # confidence in the event label. Values are in the range [0–1]
    channels: list[str]  # channels on which the event appears
    dateTime: datetime  # start date time of the recording file
    recordingDuration: float  # duration of the recording in seconds


class Annotations:
    def __init__(self):
        self.events: list[Annotation] = list()

    def getEvents(self) -> list[(float, float)]:
        events = list()
        for event in self.events:
            if event["eventType"].value in SeizureType._member_names_:
                events.append((event["onset"], event["onset"] + event["duration"]))
        return events

    def getMask(self, fs: int) -> np.ndarray:
        mask = np.zeros(int(self.events[0].recordingDuration * fs))
        for event in self.events:
            if event["eventType"].value in SeizureType._member_names_:
                mask[
                    int(event["onset"] * fs) : int(
                        (event["onset"] + event["duration"]) * fs
                    )
                ] = 1
        return mask

    def loadTsv(self, filename: str):
        print("Loading annotations")

    def saveTsv(self, filename: str):
        with open(filename, 'w') as f:
            line = '\t'.join(list(Annotation.__annotations__.keys()))
            line += '\n'
            f.write(line)
            line = ''
            for event in self.events:
                line += '{:.2f}\t'.format(event["onset"])
                line += '{:.2f}\t'.format(event["duration"])
                line += '{}\t'.format(event["eventType"].value)
                if isinstance(event["confidence"], (int, float)):
                    line += '{:.2f}\t'.format(event["confidence"])
                else:
                    line += '{}\t'.format(event["confidence"])
                if isinstance(event["channels"], (list, tuple)):
                    line += ','.join(event["channels"])
                    line += '\t'
                else:
                    line += '{}\t'.format(event["channels"])
                line += '{}\t'.format(event["dateTime"].strftime("%Y-%m-%d %H:%M:%S"))
                line += '{:.2f}'.format(event["recordingDuration"])
                line += '\n'
                f.write(line)
