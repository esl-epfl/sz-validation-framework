from datetime import datetime
import enum
import json
import os
from typing import TypedDict

import numpy as np
import pandas as pd

import dataIo

# Load Seizure types defined in the HED-SCORE JSON event file
PCKG_LOC = os.path.dirname(dataIo.__file__)
szTypes = dict()
with open(os.path.join(PCKG_LOC, "bids", "events.json"), "r") as f:
    eventsJSON = json.load(f)
    szTypes = eventsJSON["Levels"]

for key, _ in szTypes.items():
    szTypes[key] = key

SeizureType = enum.Enum("SeizureType", szTypes)

EVENT_TYPES = szTypes.copy()
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

    @classmethod
    def loadTsv(cls, filename: str):
        df = pd.read_csv(filename, delimiter="\t")
        annotations = cls()
        for _, row in df.iterrows():
            annotation = Annotation()
            annotation['onset'] = float(row['onset'])
            annotation['duration'] = float(row['duration'])
            annotation['eventType'] = EventType[row['eventType']]
            if row['confidence']:
                annotation['confidence'] = "n/a"
            else:
                annotation['confidence'] = float(row['confidence'])
            print(row['channels'])
            if row['channels']:
                annotation['channels'] = "n/a"
            elif "," in row['channels']:
                annotation['channels'] = row['channels'].split(",")
            else:
                annotation['channels'] = [row['channels']]
            annotation['dateTime'] = datetime.strptime(row['dateTime'], "%Y-%m-%d %H:%M:%S")
            annotation['recordingDuration'] = float(row['recordingDuration'])
            annotations.events.append(annotation)
    
        return annotations

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

    def saveTsv(self, filename: str):
        with open(filename, 'w') as f:
            line = '\t'.join(list(Annotation.__annotations__.keys()))
            line += '\n'
            f.write(line)
            for event in self.events:
                line = ''
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
