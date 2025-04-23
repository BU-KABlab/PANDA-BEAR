# cli/main.py
from panda_lib import toolkit

def main():
    """Entry point for PANDA-BEAR CLI"""
    from cli.menu import main_menu
    main_menu()

if __name__ == "__main__":
    main()