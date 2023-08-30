"""Script to convert EDF data to a standardized data format.

The data format is described in more detail on
https://eslweb.epfl.ch/epilepsybenchmarks/framework-for-validation-of-epileptic-seizure-detection-algorithms/#eegformat

The script can be used as a library or as a command line application.
"""
import argparse
import os
import glob
import re

import numpy as np
import pyedflib
import resampy
import pandas as pd

ELECTRODES = ('Fp1', 'F3', 'C3', 'P3', 'O1', 'F7', 'T3', 'T5', 'Fz', 'Cz', 'Pz',
              'Fp2', 'F4', 'C4', 'P4', 'O2', 'F8', 'T4', 'T6')
BIPOLAR_DBANANA = ('Fp1-F3', 'F3-C3', 'C3-P3', 'P3-O1', 'Fp1-F7', 'F7-T3', 'T3-T5', 'T5-O1', 'Fz-Cz', 'Cz-Pz',
                   'Fp2-F4', 'F4-C4', 'C4-P4', 'P4-O2', 'Fp2-F8', 'F8-T4', 'T4-T6', 'T6-O2')
FS = 256


def _getChannelIndices(channels: list[str], electrodes: tuple[str] = ELECTRODES) -> list[int]:
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
        if electrode == 'T3' or electrode == 'T7':
            electrode = '(T3|T7)'
        elif electrode == 'T4' or electrode == 'T8':
            electrode = '(T4|T8)'
        elif electrode == 'T5' or electrode == 'P7':
            electrode = '(T5|P7)'
        elif electrode == 'T6' or electrode == 'P8':
            electrode = '(T6|P8)'

        for i, channel in enumerate(channels):
            # Regex on channel name
            if re.search(r'(EEG )?{}(-REF)?'.format(electrode), channel, flags=re.IGNORECASE):
                found = True
                break
        if found:
            chIndices.append(i)
        else:
            raise ValueError("Electrode {} was not found in EDF file".format(electrode))
    return chIndices


def _getChannelIndicesBipolar(channels: list[str], electrodes: tuple[str] = BIPOLAR_DBANANA) -> list[int]:
    """Finds the index of bipolar channels in the list of channels

    Args:
        channels (list[str]): channels to extract indices
        electrodes (tuple[str]): electrodes to find. Defaults are bipolar double banana of 10-20 system.

    Raises:
        ValueError: raised if the electrode is not in the list of channels.

    Returns:
        list[int]: List containing the indices to match the list of electrodes to the list of channels
    """
    chIndices = list()
    for electrode in electrodes:
        found = False

        elecs = electrode.split('-')

        # Some channel have diffrent names in different datasets.
        for i, el in enumerate(elecs):
            if el == 'T3' or el == 'T7':
                elecs[i] = '(T3|T7)'
            elif el == 'T4' or el == 'T8':
                elecs[i]  = '(T4|T8)'
            elif el == 'T5' or el == 'P7':
                elecs[i]  = '(T5|P7)'
            elif el == 'T6' or el == 'P8':
                elecs[i]  = '(T6|P8)'

        for i, channel in enumerate(channels):
            # Regex on channel name
            regExToFind=elecs[0]+r'.*(-)?.*'+ elecs[1]
            if re.search(regExToFind, channel, flags=re.IGNORECASE):
                found = True
                break
        if found:
            chIndices.append(i)
        else:
            raise ValueError("Electrode {} was not found in EDF file".format(electrode))
    return chIndices


def loadEdf(edfFile: str, electrodes: tuple[str] = ELECTRODES, targetFs: int = FS, origMontage: str = 'mono', ref: str = 'Cz') -> np.ndarray:
    """Load an EDF file and return a numpy array corresponding to provided list of electrodes and sample frequency and
    re-referenced to Cz

    Args:
        edfFile (str): path to the EDF file
        electrodes (tuple[str]): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        targetFs (int, optional): sampling frequency. Defaults to 256.
        origMontage (str, optional): if original montage is bipolar then different search for channels. Default is 'mono'.
        ref (str, optional): reference electrode, should be in the list of electrodes (for a unipolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.

    Raises:
        ValueError: raised if ref is neither in the list of electrodes (unipolar) nor the string 'bipolar-dBanana' (bipolar).

    Returns:
        np.ndarray: 2D array of data [channels, samples]
    """
    with pyedflib.EdfReader(edfFile) as edf:
        # Get channel indices
        channels = edf.getSignalLabels()
        if origMontage == 'mono':
            chIndices = _getChannelIndices(channels, electrodes)
        else: #bipolar
            chIndices = _getChannelIndicesBipolar(channels, electrodes)

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
        if (origMontage=='mono' and ref in electrodes):   # It was unipolar and needs to be unipolar but rereferenced
            refI = electrodes.index(ref)
            eegData -= eegData[refI]
        elif (origMontage=='mono' and ref == 'bipolar-dBanana'): # It was unipolar and needs to be bipolar
            # Create reReferencing matrix
            reRefMatrix = np.zeros((len(BIPOLAR_DBANANA), len(electrodes)))
            for i, pair in enumerate(BIPOLAR_DBANANA):
                elecs = pair.split('-')
                reRefMatrix[i, electrodes.index(elecs[0])] = 1
                reRefMatrix[i, electrodes.index(elecs[1])] = -1
            eegData = reRefMatrix @ eegData  # matrix multiplication
        #last case is that it is already bipolar and needs to be exported as bipolar
        # else:
        #     raise ValueError("ref should either be one electrode (for a unipolar montage) or the string 'bipolar-dBanana' "
        #                      "(for a double banana bipolar montage).")

    return eegData


def standardizeFileToEdf(edfFile: str, outFile: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS, origMontage: str = 'mono', ref: str = 'Cz'):
    """Standardize an EDF file.

    Args:
        edfFile (str): path to the input EDF file
        outFile (str): path to the output EDF file
        electrodes (tuple[str]): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        origMontage (str, optional): if original montage is bipolar then different search for channels. Default is 'mono'.
        ref (str, optional): reference electrode, should be in the list of electrodes (for a unipolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.

    Raises:
        ValueError: raised if ref is neither in the list of electrodes (unipolar) nor the string 'bipolar-dBanana' (bipolar).
    """
    eegData = loadEdf(edfFile, electrodes, fs, origMontage, ref)

    # Build headers
    with pyedflib.EdfReader(edfFile) as edf:
        # Get channel indices
        channels = edf.getSignalLabels()
        if origMontage=='mono':
            chIndices = _getChannelIndices(channels, electrodes)
        else: #if bipolar montage in orginal dataset
            chIndices = _getChannelIndicesBipolar(channels, electrodes)

        #renaming original headers from edf files to update sampl freq and channel names
        signalHeaders = list()
        for i in range(len(eegData)):
            signalHeader = edf.getSignalHeader(chIndices[i])
            if ref in electrodes:
                signalHeader['label'] = electrodes[i]
            elif ref == 'bipolar-dBanana':
                signalHeader['label'] = BIPOLAR_DBANANA[i]
            else:
                raise ValueError("ref should either be one electrode (for a unipolar montage) or the string 'bipolar-dBanana'"
                                 " (for a double banana bipolar montage).")
            signalHeader['sample_frequency'] = fs
            signalHeader['sample_rate'] = signalHeader['sample_frequency']
            # Check for phys_maxima
            if np.max(eegData[i]) > signalHeader['physical_max'] or np.min(eegData[i]) < signalHeader['physical_min']:
                newMax = np.ceil(np.max(np.abs(eegData[i])))
                signalHeader['physical_min'] = -1 * newMax ## TODO why is min -max and not real min?
                signalHeader['physical_max'] = newMax
            signalHeaders.append(signalHeader)

        #get original recording header
        recordingHeader = edf.getHeader()
        edf._close()

    # Create directory for file
    os.makedirs(os.path.dirname(outFile), exist_ok=True)
    # Write new EDF file
    pyedflib.highlevel.write_edf(outFile, eegData, signalHeaders, recordingHeader)


def standardizeFileToDataFrame(edfFile: str, outFile: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS, origMontage: str = 'mono', ref: str = 'Cz', outFormat: str= 'parquet.gzip'):
    """Standardize EEG data to parquet.gzip file.

    Args:
        edfFile (str): path to the input EDF file
        outFile (str): path to the output EDF file
        electrodes (tuple[str]): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        origMontage (str, optional): if original montage is bipolar then different search for channels. Default is 'mono'.
        ref (str, optional): reference electrode, should be in the list of electrodes (for a unipolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.
        outFormat (str, optional): format of output file. Default is 'edf', and possibilities are 'parquet.gzip', 'csv.gzip' and 'csv'.

    Raises:
        ValueError: raised if ref is neither in the list of electrodes (unipolar) nor the string 'bipolar-dBanana' (bipolar).
    """
    eegData = loadEdf(edfFile, electrodes, fs, origMontage, ref)

    # Create dataframe with new channel names
    if ref == 'bipolar-dBanana' or origMontage!='mono':
        dataDF = pd.DataFrame(data=eegData.transpose(), columns=BIPOLAR_DBANANA)
    elif ref in electrodes:
        dataDF = pd.DataFrame(data=eegData.transpose(), columns=electrodes)
    else:
        print('ERROR: monopolar montage chosen but ref electrode not available!') #TODO make exception

    # Create directory for file
    os.makedirs(os.path.dirname(outFile), exist_ok=True)
    # Write new file
    try:
        if(outFormat == 'parquet.gzip'):  # parquet gzip
            dataDF.to_parquet(outFile[:-4] + '.'+ outFormat, index=False, compression='gzip')
        elif (outFormat == 'csv.gzip'):
            dataDF.to_csv(outFile[:-4] + '.'+ outFormat, index=False, compression='gzip')
        elif (outFormat == 'csv'):
            dataDF.to_csv(outFile[:-4] + '.'+ outFormat, index=False)
    except ValueError as exception:
        print('{}: {}'.format(exception, edfFile))

def standardizeFile(edfFile: str, outFile: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS, origMontage: str = 'mono',ref: str = 'Cz', outFormat: str= 'parquet.gzip'):
    """Standardize EEG data to output file. Type of output file depends on type parameter.

    Args:
        edfFile (str): path to the input EDF file
        outFile (str): path to the output EDF file
        electrodes (tuple[str]): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        origMontage (str, optional): if original montage is bipolar then different search for channels. Default is 'mono'.
        ref (str, optional): reference electrode, should be in the list of electrodes (for a unipolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.
        outFormat (str, optional): format of output file. Default is 'edf', and possibilities are 'parquet.gzip', 'csv.gzip' and 'csv'.

    Raises:
        ValueError: raised if ref is neither in the list of electrodes (unipolar) nor the string 'bipolar-dBanana' (bipolar).
    """
    if (origMontage!='mono'): #if person didnt specify electrodes to search, put to bipolar
        electrodes = BIPOLAR_DBANANA
        ref = 'bipolar-dBanana'

    try:
        if outFormat == 'edf':
            standardizeFileToEdf(edfFile, outFile, electrodes, fs,origMontage, ref)
        else:  # other formats but edf
            standardizeFileToDataFrame(edfFile, outFile, electrodes, fs, origMontage,ref, outFormat)
    except ValueError as exception:
        print('{}: {}'.format(exception, edfFile))


def standardizeDataset(rootDir: str, outDir: str, electrodes: tuple[str] = ELECTRODES, fs: int = FS, origMontage: str = 'mono',ref: str = 'Cz',  outFormat: str= 'edf'):
    """Converts a full dataset to the standard EEG format but exports as dataFrame in parquet.gzip format.

    Args:
        rootDir (str): root directory of the original dataset
        outDir (str): root directory of the converted dataset. The data structure of the original dataset is preserved.
        electrodes (tuple[str], optional): list of electrodes to load. Defaults to the 19 electrodes of the 10-20 system.
        fs (int, optional): sampling frequency. Defaults to 256.
        origMontage (str, optional): if original montage is bipolar then different search for channels. Default is 'mono'.
        ref (str, optional): reference electrode, should be in the list of electrodes (for a unipolar montage) or the string
                             'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'.
        outFormat (str, optional): format of output file. Default is 'edf', and possibilities are 'parquet.gzip', 'csv.gzip' and 'csv'.
    """
    if (origMontage!='mono'): #if person didnt specify electrodes to search, put to bipolar
        electrodes = BIPOLAR_DBANANA
        ref = 'bipolar-dBanana'

    # Go through all files
    # edfFiles = glob.iglob(os.path.join(rootDir, '**/*.edf'), recursive=True)
    edfFiles = np.sort(glob.glob(os.path.join(rootDir, '**/*.edf'), recursive=True))
    for edfFile in edfFiles:
        outFile= outDir+ edfFile[len(rootDir):] # swap rootDir for outDir
        try:
            if outFormat=='edf':
                standardizeFileToEdf(edfFile, outFile, electrodes, fs, origMontage, ref)
            else: #other formats but edf
                standardizeFileToDataFrame(edfFile, outFile, electrodes, fs, origMontage, ref, outFormat)
            print('Exported:' + outFile)
        except ValueError as exception:
            print('{}: {}'.format(exception, edfFile))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='EDF format standardization',
        description="Converts EDF files in a referential montage to a standardized list of electrodes and channel names. "
                    "Two formats are allowed : either conversion of full datasets by providing a directory name as input and "
                    "output or conversion of individual files by providing an edf file as input out output"
    )
    parser.add_argument('input',
                        help="either the root directory of the original dataset or the input edf file.")
    parser.add_argument('output',
                        help="either the root directory of the converted dataset or the output edf file."
                             " The data structure of the original dataset is preserved.")
    parser.add_argument('-e', '--electrodes',
                        help="List of electrodes. These should be provided as comma-separated-values. By default uses"
                        " the 19 electrodes of the 10-20 system.")
    parser.add_argument('-f', '--fs',
                        help="Sampling frequency for the converted data. Defaults to 256 Hz.", type=int, default=256)
    parser.add_argument('-m', '--origMontage',
                        help="What is original montage of the dataset, if uni(mono)polar - 'mono', if bipolar - 'bipolar'. "
                             "Defaults 'mono'",
                        default='mono')
    parser.add_argument('-r', '--ref',
                        help="Reference for the converted data. Should be in the list of electrodes (for a unipolar montage) "
                             "or the string 'bipolar-dBanana' (for a double banana bipolar montage). Defaults to 'Cz'",
                        default='Cz')
    parser.add_argument('-o', '--outFile',
                        help="Format of output file if not edf. Default is .edf ",
                        default='edf')
    args = parser.parse_args()

    # Convert list of electrodes to list
    if args.electrodes is not None:
        args.electrodes = args.electrodes.split(',')
    else:
        args.electrodes = ELECTRODES

    if os.path.isdir(args.input):
        standardizeDataset(args.input, args.output, args.electrodes, args.fs, args.origMontage, args.ref, args.outFile)
    else:
        standardizeFile(args.input, args.output, args.electrodes, args.fs, args.origMontage, args.ref, args.outFile)


