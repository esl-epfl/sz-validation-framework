# Evaluate

Evaluate the annotations produces by the seizure detection algorithm invoked in step 3.
A package named [`evaluate`](4-evaluate) is provided to do the evaluation.

The package provides a simple interface and prints results to the command line:

```python
python -m evaluate rootRefDataset rootHypDataset
```

The output is formatted as

```txt
# Sample scoring
- Sensitivity : 0.62 
- Precision   : 0.05 
- F1-score    : 0.09 
- FP/24h      : 52487.08 

# Event scoring
- Sensitivity : 1.00 
- Precision   : 0.07 
- F1-score    : 0.13 
- FP/24h      : 309.64 
```
