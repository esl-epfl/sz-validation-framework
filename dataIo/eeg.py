"""Eeg class to manipulate EEG data and associated metadata. The class interfaces with EDF files."""
import datetime
import enum
import os
import re
from typing import TypedDict

import numpy as np
from nptyping import NDArray, Shape, Float
import pandas as pd
import pyedflib
import resampy


class FileFormat(str, enum.Enum):
    CSV = "csv"
    CSV_GZIP = "csv.gzip"
    EDF = "edf"
    PARQUET_GZIP = "parquet.gzip"


class Eeg:
    class Montage(str, enum.Enum):
        UNIPOLAR = "unipolar"
        BIPOLAR = "bipolar"

    BIPOLAR_DBANANA = (
        "Fp1-F3",
        "F3-C3",
        "C3-P3",
        "P3-O1",
        "Fp1-F7",
        "F7-T3",
        "T3-T5",
        "T5-O1",
        "Fz-Cz",
        "Cz-Pz",
        "Fp2-F4",
        "F4-C4",
        "C4-P4",
        "P4-O2",
        "Fp2-F8",
        "F8-T4",
        "T4-T6",
        "T6-O2",
    )
    ELECTRODES_10_20 = (
        "Fp1",
        "F3",
        "C3",
        "P3",
        "O1",
        "F7",
        "T3",
        "T5",
        "Fz",
        "Cz",
        "Pz",
        "Fp2",
        "F4",
        "C4",
        "P4",
        "O2",
        "F8",
        "T4",
        "T6",
    )

    class SignalHeader(TypedDict):
        label: str  # channel label (string, <= 16 characters, must be unique)
        dimension: str  # physical dimension (e.g., mV) (string, <= 8 characters)
        sample_frequency: int  # number of samples per second
        physical_max: float  # maximum physical value
        physical_min: float  # minimum physical value
        digital_max: int  # maximum digital value (-2**15 <= x < 2**15)
        digital_min: int  # minimum digital value (-2**15 <= x < 2**15)

    DEFAULT_SIGNAL_HEADER: SignalHeader = {
        "label": "channel",
        "dimension": "uV",
        "sample_frequency": 256,
        "physical_max": 1e6,
        "physical_min": -1e6,
        "digital_max": 2**14,
        "digital_min": -(2**14),
    }

    class FileHeader(TypedDict):
        technician: str
        recording_additional: str
        patient_name: str
        patient_additional: str
        patient_code: str
        equipment: str
        admincode: str
        gender: int  # 1 is male, 0 is female
        recording_start_time: datetime.datetime
        birthdate: datetime.date

    DEFAULT_FILE_HEADER: FileHeader = {
        "technician": "",
        "recording_additional": "",
        "patient_name": "",
        "patient_additional": "",
        "patient_code": "",
        "equipment": "",
        "admincode": "",
        "gender": 0,
        "recording_start_time": datetime.datetime(1970, 1, 1),
        "birthdate": datetime.date(1970, 1, 1),
    }

    def __init__(
        self,
        data: NDArray[Shape["*, *"], Float],
        channels: tuple[str],
        fs: int,
        montage: Montage = Montage.UNIPOLAR,
        signalHeader: SignalHeader = DEFAULT_SIGNAL_HEADER,
        fileHeader: FileHeader = DEFAULT_FILE_HEADER,
    ):
        """Initiate an EEG instance

        Args:
            data (NDArray[Shape['*, *'], float]): data array, rows are channels, columns are samples in time
            channels (tuple[str]): tuple of channels as strings.
            fs (int): Sampling frequency.
            montage (MontageType, optional): unipolar or bipolar montage. Defaults to MontageType.UNIPOLAR.
            signalHeader (SignalHeader, optional): metadata of an EEG channel as defined by pyedflib.
                                                   Defaults to DEFAULT_SIGNAL_HEADER.
            fileHeader (FileHeader, optional): Metadata of an EEG file as defined by pyedflib. Defaults to DEFAULT_FILE_HEADER.
        """
        self.data = data
        self.channels = channels
        self.fs = fs
        self.montage = montage
        self._signalHeader = signalHeader
        self._fileHeader = fileHeader

    @classmethod
    def loadEdf(
        cls,
        edfFile: str,
        montage: Montage = Montage.UNIPOLAR,
        electrodes: list[str] = ELECTRODES_10_20,
    ):
        """Instantiate an Eeg object from an EDF file.

        Args:
            edfFile (str): path to EDF file.
            montage (Montage, optional): montage of the EEG recording. Defaults to Montage.UNIPOLAR.
            electrodes (list[str], optional): electrodes to load. If None all electrodes are loaded.
                                              For a bipolar montage, electrodes are expected in dash separated pairs
                                              (e.g. Fp1-F3). Defaults to the 19 electrodes of the 10-20 system.

        Returns:
            Eeg: returns an Eeg instance containing the data of the EDF file.
        """
        with pyedflib.EdfReader(edfFile) as edf:
            samplingFrequencies = edf.getSampleFrequencies()
            data = list()
            channels = list()
            # If electrodes are provided, load them
            if electrodes is not None:
                allChannels = edf.getSignalLabels()
                for electrode in electrodes:
                    index = Eeg._findChannelIndex(allChannels, electrode, montage)
                    data.append(edf.readSignal(index))
                    channels.append(edf.getLabel(index))
            # Else read all channels with a fixed fs
            else:
                index = 0
                fixedFs = samplingFrequencies[index]
                for i, fs in enumerate(samplingFrequencies):
                    if fixedFs == fs:
                        data.append(edf.readSignal(i))
                        channels.append(edf.getLabel(i))
            signalHeader = edf.getSignalHeader(index)
            fileHeader = edf.getHeader()
            edf._close()

        return cls(
            np.array(data),
            channels,
            samplingFrequencies[index],
            montage,
            signalHeader,
            fileHeader,
        )

    def resample(self, newFs: int):
        """Resample data to a new sampling frequency.

        Args:
            newFs (int): new sampling frequency in Hz.
        """
        self.data = resampy.resample(self.data, self.fs, newFs)
        self.fs = newFs

    def reReferenceToBipolar(self):
        """Rereference unipolar data to a double-banana bipolar montage.

        Raises:
            TypeError: raised if Eeg data is not in a unipolar montage.
        """
        if self.montage is not Eeg.Montage.UNIPOLAR:
            raise TypeError("Data must be unipolar to re-reference.")
        # Create re-referencing matrix
        reRefMatrix = np.zeros((len(Eeg.BIPOLAR_DBANANA), self.data.shape[0]))
        for i, pair in enumerate(Eeg.BIPOLAR_DBANANA):
            elecs = pair.split("-")
            for elec, multiplier in zip(elecs, (1, -1)):
                index = Eeg._findChannelIndex(self.channels, elec, self.montage)
                reRefMatrix[i, index] = multiplier

        # Rereference data
        self.data = reRefMatrix @ self.data  # matrix multiplication
        self.channels = Eeg.BIPOLAR_DBANANA
        self.montage = Eeg.Montage.BIPOLAR

    def reReferenceToCommonAverage(self):
        """Rereference unipolar data to a common average montage.

        Raises:
            TypeError: raised if Eeg data is not in a unipolar montage.
        """
        if self.montage is not Eeg.Montage.UNIPOLAR:
            raise TypeError("Data must be unipolar to re-reference.")
        self.data -= np.mean(self.data, axis=0)
        self._constructUnipolarChannelNames("Avg")

    def reReferenceToReferential(self, electrode):
        """Rereference unipolar data to a given electrode.

        Raises:
            TypeError: raised if Eeg data is not in a unipolar montage.
        """
        if self.montage is not Eeg.Montage.UNIPOLAR:
            raise TypeError("Data must be unipolar to re-reference.")
        index = Eeg._findChannelIndex(self.channels, electrode, self.montage)
        self.data -= self.data[index]
        self._constructUnipolarChannelNames(electrode)

    def standardize(
        self,
        fs: int = 256,
        electrodes: list[str] = ELECTRODES_10_20,
        reference: str = "Avg",
    ):
        """Standardize data to a given sampling frequency, with a given set of electrodes and a given reference.

        Args:
            fs (int, optional): sampling frequency in Hz. Defaults to 256.
            electrodes (list[str], optional): set of electrodes to keep. If None all electrodes are loaded.
                                              For a bipolar montage, electrodes are expected in dash separated pairs
                                              (e.g. Fp1-F3). Defaults to the 19 electrodes of the 10-20 system.
            reference (str, optional): string representing referencing schemes. Supported values are:
                                       "Avg": common average unipolar montage.
                                       "bipolar:" double banana bipolar montage.
                                       electrode: name of the reference electrode for a unipolar referential montage.
                                       Defaults to "Avg".

        Raises:
            ValueError: raised if referencing scheme is unknown
        """
        # Select electrodes
        if electrodes is not None:
            reRefMatrix = np.zeros((len(electrodes), self.data.shape[0]))
            for i, electrode in enumerate(electrodes):
                index = Eeg._findChannelIndex(self.channels, electrode, self.montage)
                reRefMatrix[i, index] = 1
            # Select data
            self.data = reRefMatrix @ self.data
            # Select channels
            indices = np.where(reRefMatrix)[1]
            self.channels = [self.channels[i] for i in indices]

        # Resample
        self.resample(fs)

        # Re-Reference
        if reference == "Avg":
            self.reReferenceToCommonAverage()
        elif reference in electrodes:
            self.reReferenceToReferential(reference)
        elif reference == "bipolar":
            # Currently we trust bipolar montage without re-referencing
            # TODO attempt to re-reference bipolar montage if possible
            if self.montage is not Eeg.Montage.BIPOLAR:
                self.reReferenceToBipolar()
        else:
            raise ValueError("Unknown referencing scheme: {}".format(reference))

    def saveEdf(self, file: str):
        """Save Eeg object to an EDF file.

        Args:
            file (str): path of the file to save to. If directory does not exist it is created.
        """
        signalHeaders = list()
        for i, channel in enumerate(self.channels):
            signalHeaders.append(self._signalHeader.copy())
            signalHeaders[i]["label"] = channel
            signalHeaders[i]["sample_frequency"] = self.fs
            signalHeaders[i]["physical_min"] = int(np.floor(np.min(self.data[i])))
            signalHeaders[i]["physical_max"] = int(np.ceil(np.max(self.data[i])))

        # Create directory for file
        if os.path.dirname(file):
            os.makedirs(os.path.dirname(file), exist_ok=True)
        # Write new EDF file
        pyedflib.highlevel.write_edf(file, self.data, signalHeaders, self._fileHeader)

    def saveDataFrame(self, file: str, format: FileFormat = FileFormat.PARQUET_GZIP):
        """Save Eeg object to a dataframe compatible file.

        Args:
            file (str):  path of the file to save to. If directory does not exist it is created.
            format (FileFormat, optional): File format to save to. Defaults to FileFormat.PARQUET_GZIP.

        Raises:
            ValueError: raised if fileFormat is not supported.
        """
        tmpData = self.data.copy()
        dataDF = pd.DataFrame(data=tmpData.transpose(), columns=self.channels)
        # TODO save metadata -- pyarrow might be a good candidate
        dataDF.attrs["fileHeader"] = self._fileHeader
        dataDF.attrs["signalHeader"] = self._signalHeader

        # Create directory for file
        if os.path.dirname(file):
            os.makedirs(os.path.dirname(file), exist_ok=True)
        # Write new file
        if format == FileFormat.PARQUET_GZIP:
            dataDF.to_parquet(file, index=False, compression="gzip")
        elif format == FileFormat.CSV_GZIP:
            dataDF.to_csv(file, index=False, compression="gzip")
        elif format == FileFormat.CSV:
            dataDF.to_csv(file, index=False)
        else:
            raise ValueError("Unknown output format {}".format(format))

    def _electrodeSynonymRegex(electrode: str) -> str:
        """Build a regex that matches the different synonyms of an electrode name.

        Args:
            electrode (str): electrode name

        Returns:
            str: regex that matches the different synonyms of an electrode name
        """
        if electrode == "T3" or electrode == "T7":
            electrode = "(T3|T7)"
        elif electrode == "T4" or electrode == "T8":
            electrode = "(T4|T8)"
        elif electrode == "T5" or electrode == "P7":
            electrode = "(T5|P7)"
        elif electrode == "T6" or electrode == "P8":
            electrode = "(T6|P8)"
        elif electrode == "O1":
            electrode = "(O1|01)"

        return electrode

    def _findChannelIndex(
        channels: tuple[str], electrode: str, montage: Montage
    ) -> int:
        """Finds the index of a channel given an electrode name.

        Args:
            channels (tuple[str]): list of channel names
            electrode (str): electrode to search for. For a bipolar montage, electrodes are expected in dash separated pairs.
            montage (Montage): montage of the data (unipolar or bipolar)

        Raises:
            ValueError: raised if electrode is not found in the list of channels

        Returns:
            int: index of the electrode in the channels array
        """
        # Some channel have different names in different datasets.
        if montage == Eeg.Montage.UNIPOLAR:
            electrode = Eeg._electrodeSynonymRegex(electrode)
        elif montage == Eeg.Montage.BIPOLAR:
            electrodes = electrode.split("-")
            for i, elec in enumerate(electrodes):
                electrodes[i] = Eeg._electrodeSynonymRegex(elec)

        # Regex on channel name
        if montage == Eeg.Montage.UNIPOLAR:
            regExToFind = r"^(EEG )?{}(-[a-z]?[1-9]*)?".format(electrode)
        elif montage == Eeg.Montage.BIPOLAR:
            regExToFind = electrodes[0] + r".*(-)?.*" + electrodes[1]

        # Find corresponding channel
        index = None
        for i, channel in enumerate(channels):
            if re.search(regExToFind, channel, flags=re.IGNORECASE):
                index = i
                break
        if index is None:
            raise ValueError("Electrode {} was not found in EDF file".format(electrode))

        return index

    def _constructUnipolarChannelNames(self, reference: str = "REF"):
        """Rename channels to a standardized name of the format ELEC-REF.

        Args:
            reference (str, optional): reference. Defaults to "REF".
        """
        regExToFind = r"^(EEG )?([A-Z]{1,2}[1-9]*)(-[a-z]?[1-9]*)?"
        for i, channel in enumerate(self.channels):
            result = re.search(regExToFind, channel, flags=re.IGNORECASE)
            if result.group(2) is not None:
                electrode = result.group(2)
            else:
                electrode = channel
            self.channels[i] = "{}-{}".format(electrode, reference)
