"""Script to convert EDF data to a standardized data format.

The data format is described in more detail on
https://eslweb.epfl.ch/epilepsybenchmarks/framework-for-validation-of-epileptic-seizure-detection-algorithms/#eegformat

The script can be used as a library or as a command line application.
"""
import argparse
import enum
import logging
import os
import glob
import re

import numpy as np
import pandas as pd
import pyedflib
import resampy

BIPOLAR_DBANANA = ('Fp1-F3', 'F3-C3', 'C3-P3', 'P3-O1', 'Fp1-F7', 'F7-T3', 'T3-T5', 'T5-O1', 'Fz-Cz', 'Cz-Pz',
                   'Fp2-F4', 'F4-C4', 'C4-P4', 'P4-O2', 'Fp2-F8', 'F8-T4', 'T4-T6', 'T6-O2')
ELECTRODES = ('Fp1', 'F3', 'C3', 'P3', 'O1', 'F7', 'T3', 'T5', 'Fz', 'Cz', 'Pz',
              'Fp2', 'F4', 'C4', 'P4', 'O2', 'F8', 'T4', 'T6')
FS = 256


class Format(str, enum.Enum):
    CSV = 'csv'
    CSV_GZIP = 'csv.gzip'
    EDF = 'edf'
    PARQUET_GZIP = 'parquet.gzip'


DATAFRAME_FORMATS = (Format.CSV, Format.CSV_GZIP, Format.PARQUET_GZIP)  # Dataframe formats


class Montage(str, enum.Enum):
    MONOPOLAR = 'mono'
    BIPOLAR = 'bipolar'


def _electrodeSynonymRegex(electrode: str) -> str:
    """Build a regex that matches the different synonims of an electrode name."""
    if electrode == 'T3' or electrode == 'T7':
        electrode = '(T3|T7)'
    elif electrode == 'T4' or electrode == 'T8':
        electrode = '(T4|T8)'
    elif electrode == 'T5' or electrode == 'P7':
        electrode = '(T5|P7)'
    elif electrode == 'T6' or electrode == 'P8':
        electrode = '(T6|P8)'

    return electrode


def _getChannelIndices(channels: list[str], electrodes: tuple[str] = ELECTRODES,
                       inputMontage: Montage = Montage.MONOPOLAR) -> list[int]:
    """Finds the index of each electrode in the list of channels

    Args:
        channels (list[str]): channels to extract indices
        electrodes (tuple[str]): electrodes to find. Defaults to the 19 electrodes of the 10-20 system.

    Raises:
        ValueError: raised if the electrode is not in the list of channels.

    Returns:
        list[int]: List containing the indices to match the list of electrodes to the list of channels
    """
    chIndices = list()
    for electrode in electrodes:
        found = False

        # Some channel have diffrent names in different datasets.
        if inputMontage == Montage.MONOPOLAR:
            electrode = _electrodeSynonymRegex(electrode)
        elif inputMontage == Montage.BIPOLAR:
            electrode = electrode.split('-')
            for i, elec in enumerate(electrode):
                electrode[i] = _electrodeSynonymRegex(elec)

        for i, channel in enumerate(channels):
            # Regex on channel name
            if inputMontage == Montage.MONOPOLAR:
                regExToFind = r'(EEG )?{}(-REF)?'.format(electrode)
            elif inputMontage == Montage.BIPOLAR:
                regExToFind = electrode[0] + r'.*(-)?.*' + electrode[1]
            if re.search(regExToFind, channel, flags=re.IGNORECASE):
                found = True
                break
        if found:
            chIndices.append(i)
        else:
            raise ValueError("Electrode {} was not found in EDF file".format(electrode))
    return chIndices


def loadEdf(edfFile: str, electrodes: tuple[str] = ELECTRODES, targetFs: int = FS, inputMontage: Montage = Montage.MONOPOLAR,
            ref: str = 'Cz') -> np.ndarray:
    """Load an EDF file and return a numpy array corresponding to provided list of electrodes, at a given sample frequency and
    re-referenced to ref

    Args:
        edfFile (str): path to the EDF file
        electrodes (tuple[str]): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        targetFs (int, optional): sampling frequency. Defaults to 256.
        inputMontage (Montage, optional): montage of dataset to load. Default is monopolar.
        ref (str, optional): reference electrode, should be in the list of electrodes (for a monopolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.

    Raises:
        NotImplementedError: when trying to load bipolar data to something else than a bipolar-dBanana.

    Returns:
        np.ndarray: 2D array of data [channels, samples]
    """
    with pyedflib.EdfReader(edfFile) as edf:
        # Get channel indices
        channels = edf.getSignalLabels()
        chIndices = _getChannelIndices(channels, electrodes, inputMontage)

        # Get Fs
        fs = edf.getSampleFrequencies()

        # Read data & resample
        eegData = list()
        for i in chIndices:
            chData = edf.readSignal(i)
            # Resample
            if fs[i] != targetFs:
                chData = resampy.resample(chData, fs[i], targetFs)
            eegData.append(chData)
        edf._close()

        # Re-reference
        eegData = np.array(eegData)
        if inputMontage == Montage.MONOPOLAR and ref in electrodes:
            refI = electrodes.index(ref)
            eegData -= eegData[refI]
            # TODO add re-referencing to common average.
        elif inputMontage == Montage.MONOPOLAR and ref == 'bipolar-dBanana':  # It was monopolar and needs to be bipolar
            # Create re-Referencing matrix
            reRefMatrix = np.zeros((len(BIPOLAR_DBANANA), len(electrodes)))
            for i, pair in enumerate(BIPOLAR_DBANANA):
                elecs = pair.split('-')
                reRefMatrix[i, electrodes.index(elecs[0])] = 1
                reRefMatrix[i, electrodes.index(elecs[1])] = -1
            eegData = reRefMatrix @ eegData  # matrix multiplication
        elif inputMontage == Montage.BIPOLAR and ref == 'bipolar-dBanana' and electrodes == BIPOLAR_DBANANA:
            # Currently only supports loading bipolar data if target is bipolar-dBanana.
            pass
        else:
            raise NotImplementedError("Currently bipolar data can only be converted to a standard bipolar-dBanana montage.")

    return eegData


def standardizeFileToEdf(edfFile: str, outFile: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS,
                         inputMontage: Montage = Montage.MONOPOLAR, ref: str = 'Cz'):
    """Convert an EEG EDF file to a standardized EDF.

    The function allows loading monopolar or bipolar EDF files (specified by `inputMontage`).
    The data is then converted to a standardized sampling frequency (`fs`) and re-referenced according to `electrodes` and
    `ref`. The data is then saved to EDF.

    Args:
        edfFile (str): path to the input EDF file
        outFile (str): path to the output file
        electrodes (tuple[str], optional): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        inputMontage (Montage, optional): montage of dataset to load. Default is monopolar.
        ref (str, optional): reference electrode. Should be in the list of electrodes (for a monopolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.

    Raises:
        ValueError: raised if ref is neither in the list of electrodes (monopolar) nor the string 'bipolar-dBanana' (bipolar).
    """
    eegData = loadEdf(edfFile, electrodes, fs, inputMontage, ref)

    # Build headers
    with pyedflib.EdfReader(edfFile) as edf:
        # Get channel indices
        channels = edf.getSignalLabels()
        chIndices = _getChannelIndices(channels, electrodes, inputMontage)

        # rename original headers from edf files to update sample frequency and channel names
        signalHeaders = list()
        for i in range(len(eegData)):
            signalHeader = edf.getSignalHeader(chIndices[i])
            # Channel Label
            if ref in electrodes:
                signalHeader['label'] = '{}-{}'.format(electrodes[i], ref)
            elif ref == 'bipolar-dBanana':
                signalHeader['label'] = BIPOLAR_DBANANA[i]
            else:
                raise ValueError("ref should either be an electrode (for a monopolar montage) or the string 'bipolar-dBanana'"
                                 " (for a double banana bipolar montage).")
            # Channel Fs (old and new pyedflib names)
            signalHeader['sample_frequency'] = fs
            signalHeader['sample_rate'] = signalHeader['sample_frequency']
            # Update physical extrema (could change due to re-referencing)
            if np.max(eegData[i]) > signalHeader['physical_max'] or np.min(eegData[i]) < signalHeader['physical_min']:
                newMax = np.ceil(np.max(np.abs(eegData[i])))
                signalHeader['physical_min'] = -1 * newMax
                signalHeader['physical_max'] = newMax
            signalHeaders.append(signalHeader)

        # get original recording header
        recordingHeader = edf.getHeader()
        edf._close()

    # Create directory for file
    if os.path.dirname(outFile):
        os.makedirs(os.path.dirname(outFile), exist_ok=True)
    # Write new EDF file
    pyedflib.highlevel.write_edf(outFile, eegData, signalHeaders, recordingHeader)


def standardizeFileToDataFrame(edfFile: str, outFile: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS,
                               inputMontage: Montage = Montage.MONOPOLAR, ref: str = 'Cz',
                               outDataFrameFormat: Format = Format.PARQUET_GZIP):
    """Convert an EEG EDF file to a standardized DataFrame format.

    The function allows loading monopolar or bipolar EDF files (specified by `inputMontage`).
    The data is then converted to a standardized sampling frequency (`fs`) and re-referenced according to `electrodes` and
    `ref`. The data is then saved in one of the supported formats (outFormat: Format).

    Args:
        edfFile (str): path to the input EDF file
        outFile (str): path to the output file
        electrodes (tuple[str], optional): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        inputMontage (Montage, optional): montage of dataset to load. Default is monopolar.
        ref (str, optional): reference electrode. Should be in the list of electrodes (for a monopolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.
        outDataFrameFormat (Format, optional): format of the output file. Supported formats are csv, csv.gzip, parquet.gzip.
                                      Default is parquet.gzip.

    Raises:
        ValueError: raised if ref is neither in the list of electrodes (monopolar) nor the string 'bipolar-dBanana' (bipolar).
        ValueError: if outDataFrameFormat is unknown
    """
    eegData = loadEdf(edfFile, electrodes, fs, inputMontage, ref)

    # Create dataframe with new channel names
    if ref in electrodes:
        dataDF = pd.DataFrame(data=eegData.transpose(), columns=('{}-{}'.format(x, ref) for x in electrodes))
    elif ref == 'bipolar-dBanana':
        dataDF = pd.DataFrame(data=eegData.transpose(), columns=BIPOLAR_DBANANA)
    else:
        raise ValueError("ref should either be an electrode (for a monopolar montage) or the string 'bipolar-dBanana'"
                         " (for a double banana bipolar montage).")

    # TODO check if extra metadata can be added to the different DataFrame formats

    # Create directory for file
    if os.path.dirname(outFile):
        os.makedirs(os.path.dirname(outFile), exist_ok=True)
    # Write new file
    if outDataFrameFormat == Format.PARQUET_GZIP:
        dataDF.to_parquet(outFile, index=False, compression='gzip')
    elif outDataFrameFormat == Format.CSV_GZIP:
        dataDF.to_csv(outFile, index=False, compression='gzip')
    elif outDataFrameFormat == Format.CSV:
        dataDF.to_csv(outFile, index=False)
    else:
        raise ValueError('Unknown output format {}'.format(outDataFrameFormat))


def standardizeFile(edfFile: str, outFile: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS,
                    inputMontage: Montage = Montage.MONOPOLAR, ref: str = 'Cz', outFormat: Format = Format.EDF):
    """Convert an EEG EDF file to a standardized format.

    The function allows loading monopolar or bipolar EDF files (specified by `inputMontage`).
    The data is then converted to a standardized sampling frequency (`fs`) and re-referenced according to `electrodes` and
    `ref`. The data is then saved in one of the supported formats (outFormat: Format).

    Args:
        edfFile (str): path to the input EDF file
        outFile (str): path to the output file
        electrodes (tuple[str], optional): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        inputMontage (Montage, optional): montage of dataset to load. Default is monopolar.
        ref (str, optional): reference electrode. Should be in the list of electrodes (for a monopolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.
        outFormat (Format, optional): format of the output file. Supported formats are edf, csv, csv.gzip, parquet.gzip.
                                      Default is edf.

    Raises:
        ValueError: if outDataFrameFormat is unknown.
    """
    if outFormat == Format.EDF:
        standardizeFileToEdf(edfFile, outFile, electrodes, fs, inputMontage, ref)
    elif outFormat in DATAFRAME_FORMATS:
        standardizeFileToDataFrame(edfFile, outFile, electrodes, fs, inputMontage, ref, outFormat)
    else:
        raise ValueError('Unknown output format {}'.format(outFormat))


def standardizeDataset(rootDir: str, outDir: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS,
                       inputMontage: Montage = Montage.MONOPOLAR, ref: str = 'Cz', outFormat: Format = Format.EDF):
    """Converts a full dataset to the standard EEG format.
    ! If conversion of a file fails, a logging error is printed and processing of other files continues.

    Args:
        rootDir (str): root directory of the original dataset
        outDir (str): root directory of the converted dataset. The data structure of the original dataset is preserved.
        electrodes (tuple[str], optional): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        inputMontage (Montage, optional): montage of dataset to load. Default is monopolar.
        ref (str, optional): reference electrode, should be in the list of electrodes (for a monopolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.
        outFormat (Format, optional): format of output file. Supported formats are edf, csv, csv.gzip, parquet.gzip.
                                      Default is edf.

    Raises:
        ValueError: if outDataFrameFormat is unknown.
    """
    # Go through all files
    edfFiles = glob.iglob(os.path.join(rootDir, '**/*.edf'), recursive=True)
    for edfFile in edfFiles:
        try:
            if outFormat == Format.EDF:
                outFile = os.path.join(outDir, edfFile[len(rootDir):])
                standardizeFileToEdf(edfFile, outFile, electrodes, fs, inputMontage, ref)
            elif outFormat in DATAFRAME_FORMATS:
                outFile = os.path.join(outDir, edfFile[len(rootDir):-3] + outFormat)
                standardizeFileToDataFrame(edfFile, outFile, electrodes, fs, inputMontage, ref, outFormat)
            else:
                raise ValueError('Unknown output format {}'.format(outFormat))
            logging.info('Converted {}'.format(edfFile))
        except ValueError as exception:
            logging.error('Error converting {} \n {}'.format(edfFile, exception))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='EDF format standardization',
        description="Converts EDF files in a montage to a standardized list of electrodes and channel names. "
                    "Two formats are allowed : either conversion of full datasets by providing a directory name as input and "
                    "conversion of individual files by providing an edf file as input"
    )
    parser.add_argument('input',
                        help="either the root directory of the original dataset or the input edf file.")
    parser.add_argument('output',
                        help="either the root directory of the converted dataset or the output filename."
                             " The data structure of the original dataset is preserved.")
    parser.add_argument('-e', '--electrodes',
                        help="List of electrodes. These should be provided as comma-separated-values. By default uses"
                        " the 19 electrodes of the 10-20 system.")
    parser.add_argument('-f', '--fs',
                        help="Sampling frequency for the converted data. Defaults to 256 Hz.", type=int, default=256)
    parser.add_argument('-m', '--inputMontage',
                        help="Montage of the input, if uni(mono)polar - 'mono', if bipolar - 'bipolar'. "
                             "Defaults 'mono'",
                        default='mono')
    parser.add_argument('-r', '--ref',
                        help="Reference for the converted data. Should be in the list of electrodes (for a monopolar montage) "
                             "or the string 'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'",
                        default='Cz')
    parser.add_argument('-o', '--outFormat',
                        help="Format of the output file. Should be one of 'edf', 'csv, 'csv.gzip', 'parquet.gzip'. "
                             "Default is .edf ",
                        default='edf')
    args = parser.parse_args()

    # Convert list of electrodes to list
    if args.electrodes is not None:
        args.electrodes = args.electrodes.split(',')
    elif args.inputMontage == Montage.BIPOLAR:
        args.electrodes = BIPOLAR_DBANANA
    else:
        args.electrodes = ELECTRODES

    if os.path.isdir(args.input):
        standardizeDataset(args.input, args.output, args.electrodes, args.fs, args.inputMontage, args.ref, args.outFormat)
    else:
        standardizeFile(args.input, args.output, args.electrodes, args.fs, args.inputMontage, args.ref, args.outFormat)
