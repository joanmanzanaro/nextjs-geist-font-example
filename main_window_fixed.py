import os
os.environ['QT_QPA_PLATFORM'] = 'minimal'

from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo Gallery")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add a label
        label = QLabel("Photo Gallery Application")
        layout.addWidget(label)
        
        print("Window initialized successfully")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    print("Application created successfully")
    window.show()
    print("Window shown")
    return app.exec()

if __name__ == "__main__":
    main()
