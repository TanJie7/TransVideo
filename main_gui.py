
import sys
import logging
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Cleaner look than default Windows
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
