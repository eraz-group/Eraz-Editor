import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit
from PyQt6.QtCore import QProcess

class TerminalWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        layout.addWidget(self.terminal_output)

        self.input_line = QLineEdit()
        self.input_line.returnPressed.connect(self.execute_command)
        layout.addWidget(self.input_line)

        self.setLayout(layout)

        # Start the terminal process
        self.process = QProcess()
        shell = "cmd.exe" if os.name == "nt" else "bash"
        self.process.start(shell)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_output)
    
    def execute_command(self):
        command = self.input_line.text().strip()
        if command:
            self.terminal_output.appendPlainText(f"> {command}")
            self.process.write((command + "\n").encode())
        self.input_line.clear()
    
    def read_output(self):
        # Determine the appropriate encoding based on the operating system
        encoding = "cp1252" if os.name == "nt" else "utf-8"

        # Read and decode the standard output and error output
        output = self.process.readAllStandardOutput().data().decode(encoding, errors="replace")
        error_output = self.process.readAllStandardError().data().decode(encoding, errors="replace")

        # Append the output to the terminal
        if output:
            self.terminal_output.appendPlainText(output)
        if error_output:
            self.terminal_output.appendPlainText(error_output)
