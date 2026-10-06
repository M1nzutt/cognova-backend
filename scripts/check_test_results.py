"""CI must not silently pass when PostgreSQL integration tests were skipped."""

import sys
import xml.etree.ElementTree as ET


def main() -> None:
    root = ET.parse(sys.argv[1]).getroot()
    if any(int(suite.get("skipped", "0")) for suite in root.iter("testsuite")):
        raise SystemExit("CI requires all tests, including real PostgreSQL integration")


if __name__ == "__main__":
    main()
