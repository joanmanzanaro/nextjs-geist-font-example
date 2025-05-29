import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication, QMainWindow
import sys

class SimpleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Window initialized")

def main():
    app = QApplicationI encountered an error writing the file. Let me try a simpler approach to modify the test_window.py file to set the offscreen platform environment variable.

<edit_file>
<path>test_window.py</path>
<content>
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication, QMainWindow
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Window")
        self.setGeometry(100, 100, 800, 600)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
