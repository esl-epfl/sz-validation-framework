import glob
import os
import shutil
from string import Template

import pandas as pd

import dataIo
from dataIo.eeg import Eeg
from dataIo.load_annotations.load_annotations_chb import loadAnnotationsFromEdf

PCKG_LOC = os.path.dirname(dataIo.__file__)


def convert(root: str, outDir: str):
    subjects = []
    for _, directory, _ in os.walk(root):
        for subject in directory:
            subjects.append(subject)
    for folder in subjects:
        print(folder)
        # Extract subject & session ID
        subject = os.path.split(folder)[-1][3:5]
        session = "01"
        task = "szMonitoring"
        if subject == "21":
            subject = "01"
            session = "02"

        # Create BIDS hierarchy
        outPath = os.path.join(
            outDir, "sub-{}".format(subject), "ses-{}".format(session), "eeg"
        )
        os.makedirs(outPath, exist_ok=True)

        edfFiles = sorted(glob.glob(os.path.join(root, folder, "*.edf")))
        for fileIndex, edfFile in enumerate(edfFiles):
            edfBaseName = os.path.join(
                outPath,
                "sub-{}_ses-{}_task-{}_run-{:02}_eeg".format(
                    subject, session, task, fileIndex
                ),
            )
            edfFileName = edfBaseName + ".edf"
            # Load EEG and standardize it
            if os.path.basename(edfFile) not in (
                "chb12_27.edf",
                "chb12_28.edf",
                "chb12_29.edf",
            ):
                eeg = Eeg.loadEdf(edfFile, Eeg.Montage.BIPOLAR, Eeg.BIPOLAR_DBANANA)
                eeg.standardize(256, Eeg.BIPOLAR_DBANANA, "bipolar")
            else:
                eeg = Eeg.loadEdf(edfFile, Eeg.Montage.UNIPOLAR, Eeg.ELECTRODES_10_20)
                eeg.standardize(256, Eeg.ELECTRODES_10_20, "bipolar")

            # Save EEG
            eeg.saveEdf(edfFileName)

            # Save JSON sidecar
            eegJsonDict = {
                "fs": "{}".format(int(eeg.fs)),
                "channels": "{}".format(eeg.data.shape[0]),
                "duration": "{:.2f}".format(eeg.data.shape[1] / eeg.fs),
                "task": task,
            }

            with open(os.path.join(PCKG_LOC, "bids", "eeg_chbmit.json"), "r") as f:
                src = Template(f.read())
                eegJsonSidecar = src.substitute(eegJsonDict)
            with open(edfBaseName + ".json", "w") as f:
                f.write(eegJsonSidecar)

            # Load annotation
            annotations = loadAnnotationsFromEdf(edfFile)
            annotations.saveTsv(edfBaseName + ".tsv")

    # Build participant metadata
    subjectInfo = pd.read_csv(
        os.path.join(root, "SUBJECT-INFO"), delimiter="\t", skip_blank_lines=True
    )
    participants = {"participant_id": [], "age": [], "sex": [], "comment": []}
    for folder in glob.iglob(os.path.join(outDir, "sub-*")):
        subject = os.path.split(folder)[-1]
        originalSubjectName = "chb{}".format(subject[4:6])
        if originalSubjectName in subjectInfo.Case.values:
            participants["participant_id"].append(subject)
            participants["age"].append(
                subjectInfo[subjectInfo.Case == originalSubjectName][
                    "Age (years)"
                ].values[0]
            )
            participants["sex"].append(
                subjectInfo[subjectInfo.Case == originalSubjectName]
                .Gender.values[0]
                .lower()
            )
            if subject == "sub-01":
                participants["comment"].append("ses-02 recorded at 13 years old")
            else:
                participants["comment"].append("")

        else:
            participants["participant_id"].append(subject)
            participants["age"].append("n/a")
            participants["sex"].append("n/a")
            participants["comment"].append("")

    participantsDf = pd.DataFrame(participants)
    participantsDf.sort_values(by=["participant_id"], inplace=True)
    participantsDf.to_csv(
        os.path.join(outDir, "participants.tsv"), sep="\t", index=False
    )
    participantsJsonFileName = os.path.join(PCKG_LOC, "bids", "participants.json")
    shutil.copy(participantsJsonFileName, outDir)

    # Copy Readme file
    readmeFileName = os.path.join(PCKG_LOC, "bids", "README_chbmit.md")
    shutil.copyfile(readmeFileName, os.path.join(outDir, "README"))

    # Copy dataset description
    descriptionFileName = os.path.join(
        PCKG_LOC, "bids", "dataset_description_chbmit.json"
    )
    shutil.copyfile(
        descriptionFileName, os.path.join(outDir, "dataset_description.json")
    )
