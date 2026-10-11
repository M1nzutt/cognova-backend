"""CI must not silently pass when PostgreSQL integration tests were skipped."""

import sys
import xml.etree.ElementTree as ET


def main() -> None:
    root = ET.parse(sys.argv[1]).getroot()
    cases = list(root.iter("testcase"))
    integration = [
        case for case in cases if ".integration." in case.get("classname", "")
    ]
    if not integration or any(
        case.find(tag) is not None
        for case in cases
        for tag in ("skipped", "failure", "error")
    ):
        raise SystemExit("CI requires successful, unskipped PostgreSQL integration")
    print(f"Verified {len(cases)} tests including {len(integration)} PostgreSQL cases")


if __name__ == "__main__":
    main()
