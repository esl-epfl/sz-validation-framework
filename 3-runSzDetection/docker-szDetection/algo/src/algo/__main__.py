if __name__ == "__main__":
    import argparse
    from algo.sz_detection import szDetection

    parser = argparse.ArgumentParser(
        description="Run a seizure detection algorithm on an EDF file and store computed seizure annotations to a TSV."
    )
    parser.add_argument("input", help="Path to the input EDF EEG file.")
    parser.add_argument("output", help="Path to the output TSV annotation file.")

    args = parser.parse_args()
    szDetection(args.input, args.output)
