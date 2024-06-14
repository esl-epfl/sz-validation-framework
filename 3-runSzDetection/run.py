import argparse
from pathlib import Path
import subprocess

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run dockerized sz detection on all EEG files"
    )
    parser.add_argument("input", help="Path to root of the EDF EEG files.")
    args = parser.parse_args()

    for edf in Path(args.input).glob("**/*.edf"):
        input = edf.relative_to(args.input)
        print(input)
        
        output = edf.relative_to(args.input).as_posix()[:-8] + "_events.tsv"
        subprocess.run( 
            [
                "docker",
                "compose",
                "run",
                "-e",
                f"INPUT={input}",
                "-e"
                f"OUTPUT={output}",
                "sz_detection",
            ],
            cwd="docker-szDetection"
        )
