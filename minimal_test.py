import os
os.environ['QT_QPA_PLATFORM'] = 'minimal'

from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
import sys

class MinimalWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minimal Test")
        self.setGeometry(100, 100, 400, 300)
        
        label = QLabel("Test Window Running in Minimal Mode")
        self.setCentralWidget(label)
        
        print("Window initialized successfully")

def main():
    app = QApplication(sys.argv)
    window = MinimalWindow()
    print("Application created successfully")
    window.show()
    print("Window shown")
    return app.exec()

if __name__ == "__main__":
    main()
