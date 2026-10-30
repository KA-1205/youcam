"""Worker entry point; foundation never claims or dispatches jobs."""
import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps({"status": "FOUNDATION", "dispatchEnabled": False}))


if __name__ == "__main__":
    main()
