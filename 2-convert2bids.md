# Convert datasets to BIDS

All datasets store the EEG data and the seizure annotations differently. They use a different folder structure, different sampling frequencies, channels and reference for the EEG, and different formats for the annotations. This complicates development of algorithms that are intended to run on any dataset. The [Brain Imaging Data Structure](https://bids.neuroimaging.io/) (BIDS) provides a strandardized organization of neuroimaging studies.

The [`epilepsy2bids`](https://github.com/esl-epfl/epilepsy2bids) package converts the main epilepsy datasets to BIDS compliant datasets. The conversion is opinionated to make all datasets as similar as possible.

Converted EDF files contain :

- Unipolar channels are referenced to a common average montage
- Data is sampled at 256 Hz
- Only the 19 electrodes of the 10-20 montage

*The Physionet CHB-MIT Scalp EEG Database is converted to a bipolar double-banana montage.*

The [`epilepsy2bids`](https://github.com/esl-epfl/epilepsy2bids) package provides a straightforward interface to convert datasets:

```python
from epilepsy2bids.bids.chbmit.convert2bids import convert

convert(root: Path, outDir: Path)
```

*Each dataset implements it's own converter in epilepsy2bids.bids.[chbmit, siena, tuh, seizeit].*
