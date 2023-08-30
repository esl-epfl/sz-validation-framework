''' Class to store annotations both as a binary mask and as a list of events.
'''

__author__ = "Jonathan Dan"
__email__ = "jonathan.dan at epfl.ch"

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from nptyping import Bool, NDArray, Shape


@dataclass(frozen=True)
class Annotation:
    """Class to store annotations both as a binary mask and as a list of events.

    Instances can be initiated either from a a binary mask or from a list of events,
    the other data representation will be automatically generated. The class properties
    are immutable to guarantee consistency between both data types.
    """
    events: List[Tuple[int, int]]
    mask: NDArray[Shape["Size"], Bool]
    fs: int

    def __init__(self, data, fs: int, numSamples: int = None):
        """Initialize an annotation instance.
        - Annotation(mask, fs):
        This can either be done by providing a binary vector where positive labels are
        indicated by True.

        - Annotation(events, fs, numSamples)
        Or by provding a list of (start, stop) tuples for each event. Start and stop
        times are expected in seconds.

        The annotation class contains two immutable fields: mask and events.

        Args:
            data (List[Tuple[int, int]] OR NDArray[Bool]): _description_
            fs (int): Sampling frequency in Hertz of the annotations.
            numSamples (int, optional): Is required when initalizing by providing a
                list of (start, stop) tuples. It indicates the number of annotation
                samples in the annotation binary mask. It should be left to None if
                a binary mask is provided. Defaults to None.

        Raises:
            TypeError: Raises a TypeError if input does not meet one of the expected
                data types.
        """
        object.__setattr__(self, 'fs', fs)  # Write to frozen object
        # Annotation(events, fs, numSamples)
        # Init by providing a list of start, stop tuples for each event
        if numSamples is not None:
            # Build binary mask associated with list of events
            mask = np.zeros((numSamples, ), dtype=np.bool_)
            for event in data:
                mask[round(event[0] * fs):round(event[1] * fs)] = True
            object.__setattr__(self, 'events', data)  # Write to frozen object
            object.__setattr__(self, 'mask', mask)  # Write to frozen object

        # Annotation(mask, fs)
        # Init provided by a binary mask with True labels during event
        elif numSamples is None:
            events = list()
            tmpEnd = []
            # Find transitions
            start_i = np.where(np.diff(np.array(data, dtype=int)) == 1)[0]
            end_i = np.where(np.diff(np.array(data, dtype=int)) == -1)[0]

            # No transitions and first sample is positive -> event is duration of file
            if len(start_i) == 0 and len(end_i) == 0 and data[0]:
                events.append((0, len(data) / fs))
            else:
                # Edge effect - First sample is an event
                if data[0]:
                    events.append((0, (end_i[0] + 1) / fs))
                    end_i = np.delete(end_i, 0)
                # Edge effect - Last event runs until end of file
                if data[-1]:
                    if len(start_i):
                        tmpEnd = [((start_i[-1] + 1) / fs, len(data) / fs)]
                        start_i = np.delete(start_i, len(start_i) - 1)
                # Add all events
                start_i += 1
                end_i += 1
                for i in range(len(start_i)):
                    events.append((start_i[i] / fs, end_i[i] / fs))
                events += tmpEnd  # add potential end edge effect
            object.__setattr__(self, 'events', events)  # Write to frozen object
            object.__setattr__(self, 'mask', np.array(data, dtype=np.bool_))  # Write to frozen object

        else:
            raise TypeError
