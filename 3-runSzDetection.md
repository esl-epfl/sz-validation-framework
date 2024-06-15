# Run a seizure detection algorithm

It is expected that seizure detection algorithms are packaged as docker containers.

An example of a python package that performs seizure detection is provided in [`3-runSzDetection/docker-szDetection/algo`](3-runSzDetection/docker-szDetection/algo). The python package takes the EEG `.edf` file and output annotations `.tsv` file as input arguments:

```python
python -m algo input.edf output.tsv
```

The python package is containerized in a docker container that is responsible for installing all package dependencies. The [`Dockerfile`](3-runSzDetection/docker-szDetection/Dockerfile) provides a template that can be used to package python packages.

The docker container can then be invoked to analyze an EEG file:

```bash
docker compose run -e INPUT="input.edf" -e OUTPUT="output.tsv" sz_detection
```

A python script ([`run.py`](3-runSzDetection/run.py)) is responsible for running the seizure detection algorithm on all available EEG files.
