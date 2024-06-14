if __name__ == "__main__":
    import argparse
    from evaluate.evaluate import evaluate

    parser = argparse.ArgumentParser(
        description="Evaluation code to compare annotations from a seizure detection algorithm to ground truth annotations."
    )
    parser.add_argument("ref", help="Path to the root folder containing the reference annotations.")
    parser.add_argument("hyp", help="Path to the root folder containing the hypothesis annotations.")

    args = parser.parse_args()
    evaluate(args.ref, args.hyp)