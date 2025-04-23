import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Now you can import modules from src
from cli.menu.main_menu import main

if __name__ == "__main__":
    main()
