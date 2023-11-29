""" Eeg class unit testing
"""

import unittest

from dataIo.eeg import Eeg, FileFormat


class TestDataLoading(unittest.TestCase):
    def test_loadEdf(self):
        fileConfigurations = [
            {  # CHB-MIT
                "fileName": "dataIo/test/chb01_01_sample.edf",
                "montage": Eeg.Montage.BIPOLAR,
                "electrodes": Eeg.BIPOLAR_DBANANA,
            },
            {  # TUH
                "fileName": "dataIo/test/aaaaaaac_s001_t000_sample.edf",
                "montage": Eeg.Montage.UNIPOLAR,
                "electrodes": Eeg.ELECTRODES_10_20,
            },
            {  # Siena
                "fileName": "dataIo/test/PN00-5_sample.edf",
                "montage": Eeg.Montage.UNIPOLAR,
                "electrodes": Eeg.ELECTRODES_10_20,
            },
            {  # SeizeIT
                "fileName": "dataIo/test/P_ID10_r5_sample.edf",
                "montage": Eeg.Montage.UNIPOLAR,
                "electrodes": Eeg.ELECTRODES_10_20,
            },
        ]

        for fileConfig in fileConfigurations:
            eeg = Eeg.loadEdf(
                fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
            )

            self.assertEqual(eeg.data.shape[0], len(fileConfig["electrodes"]))
            self.assertEqual(len(eeg.channels), len(fileConfig["electrodes"]))
            self.assertEqual(eeg.montage, fileConfig["montage"])

    def test_resampling(self):
        fileConfig = {  # Siena
            "fileName": "dataIo/test/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        fileDuration = eeg.data.shape[1] / eeg.fs
        newFs = 256
        eeg.resample(newFs)
        newFileDuration = eeg.data.shape[1] / newFs

        self.assertEqual(fileDuration, newFileDuration)
        self.assertEqual(eeg.fs, newFs)

    def test_reReference(self):
        fileConfig = {  # Siena
            "fileName": "dataIo/test/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        eeg.reReferenceToCommonAverage()
        eeg.reReferenceToReferential("Cz")
        eeg.reReferenceToBipolar()
        # TODO write tests
        eeg.standardize(electrodes=Eeg.BIPOLAR_DBANANA, reference="bipolar")

    def test_saveEdf(self):
        fileConfig = {  # Siena
            "fileName": "dataIo/test/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        # TODO write tests
        eeg.standardize()
        eeg.saveEdf("test.edf")

    def test_savecsv(self):
        fileConfig = {  # Siena
            "fileName": "dataIo/test/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        # TODO write tests
        eeg.standardize()
        eeg.saveDataFrame("test.csv", FileFormat.CSV)


if __name__ == "__main__":
    unittest.main()
