import sys
from pathlib import Path

# Add project root directory to path to ensure absolute FSD imports work correctly
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.cli import main

if __name__ == "__main__":
    main()
