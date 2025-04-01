import sys
import os
import subprocess
import re

from PyQt6.QtCore import Qt, QDir, QRect, QPropertyAnimation, QTimer
from PyQt6.QtGui import QFileSystemModel, QKeySequence, QPainter, QColor, QAction, QTextCharFormat, QSyntaxHighlighter, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPlainTextEdit, QTabWidget,
    QSplitter, QMessageBox, QVBoxLayout, QWidget, QTreeView, QLineEdit, QTextEdit,
    QGraphicsDropShadowEffect
)

from terminal import TerminalWidget

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(75)  # 75 = QFont.Bold
        keywords = [
            'def', 'class', 'if', 'elif', 'else', 'while', 'for', 'try', 'except', 'finally',
            'with', 'as', 'return', 'import', 'from', 'pass', 'break', 'continue', 'in', 'not', 'and', 'or', 'is', 'lambda'
        ]
        for word in keywords:
            pattern = re.compile(rf'\b{word}\b')
            self.highlighting_rules.append((pattern, keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        self.highlighting_rules.append((re.compile(r'(\".*?\"|\'.*?\')'), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.highlighting_rules.append((re.compile(r'#.*'), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

class LiveLintingMixin:
    def setup_linting(self):
        self.lint_timer = QTimer(self)
        self.lint_timer.setInterval(1000)
        self.lint_timer.timeout.connect(self.run_linting)
        self.textChanged.connect(self.lint_timer.start)
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(QColor("red"))
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)

    def run_linting(self):
        self.lint_timer.stop()
        code = self.toPlainText()
        path = "temp_lint.py"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)

        try:
            result = subprocess.run(["flake8", path], capture_output=True, text=True)
            self.clear_lint_marks()
            if result.stdout:
                for line in result.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        try:
                            lineno = int(parts[1]) - 1
                            cursor = QTextCursor(self.document().findBlockByNumber(lineno))
                            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
                            cursor.setCharFormat(self.error_format)
                        except ValueError:
                            continue
        except Exception as e:
            pass

    def clear_lint_marks(self):
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())

class EditorWithLines(QPlainTextEdit, LiveLintingMixin):
    def __init__(self, parent, editor_code):
        super().__init__(parent)
        self.editor_code = editor_code
        self.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 14px; border-radius: 6px; padding: 4px;")
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))

        self.highlighter = PythonHighlighter(self.document())
        self.setup_linting()

        self.file_extension = None

    def set_file_extension(self, ext):
        self.file_extension = ext

    def get_file_extension(self):
        return self.file_extension

class EditeurCode(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eraz Editor Professional")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("background-color: #2d2d30; color: #dcdcdc;")

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)
        self.splitter.setSizes([250, 1150])

        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.file_explorer = QTreeView()
        self.file_explorer.setModel(self.file_model)
        self.file_explorer.setRootIndex(self.file_model.index(""))
        self.file_explorer.setStyleSheet("background-color: #252526; color: #dcdcdc; border-radius: 5px;")
        self.file_explorer.doubleClicked.connect(self.ouvrir_fichier_depuis_explorateur)
        self.splitter.addWidget(self.file_explorer)

        right_widget = QWidget()
        right_layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.fermer_onglet)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background: #2d2d30;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #3c3c3c;
                color: #dcdcdc;
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #007acc;
                color: white;
            }
        """)
        right_layout.addWidget(self.tabs)

        self.terminal = TerminalWidget()
        self.terminal.setStyleSheet("background-color: #252526; color: #dcdcdc; border-radius: 5px;")
        self.terminal.setFixedHeight(200)
        right_layout.addWidget(self.terminal)

        right_widget.setLayout(right_layout)
        self.splitter.addWidget(right_widget)

        self.command_bar = QLineEdit(self)
        self.command_bar.setPlaceholderText("Enter command")
        self.command_bar.setStyleSheet("background-color: #252526; color: #dcdcdc; border: none; padding: 5px; border-radius: 5px;")
        self.command_bar.returnPressed.connect(self.execute_command_from_bar)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.splitter)
        main_layout.addWidget(self.command_bar)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        menu = self.menuBar()
        fichier_menu = menu.addMenu("Fichier")

        ouvrir_action = QAction("Ouvrir fichier", self)
        ouvrir_action.setShortcut(QKeySequence("Ctrl+O"))
        ouvrir_action.triggered.connect(self.ouvrir_fichier)
        fichier_menu.addAction(ouvrir_action)

        ouvrir_dossier_action = QAction("Ouvrir dossier", self)
        ouvrir_dossier_action.setShortcut(QKeySequence("Ctrl+D"))
        ouvrir_dossier_action.triggered.connect(self.ouvrir_dossier)
        fichier_menu.addAction(ouvrir_dossier_action)

        creer_fichier_action = QAction("Créer fichier", self)
        creer_fichier_action.setShortcut(QKeySequence("Ctrl+N"))
        creer_fichier_action.triggered.connect(self.creer_fichier)
        fichier_menu.addAction(creer_fichier_action)

        sauvegarder_action = QAction("Sauvegarder fichier", self)
        sauvegarder_action.setShortcut(QKeySequence("Ctrl+S"))
        sauvegarder_action.triggered.connect(self.sauvegarder_fichier)
        fichier_menu.addAction(sauvegarder_action)

        self.dossier_actuel = ""
        self.tab_data = {}

    def execute_command_from_bar(self):
        command = self.command_bar.text().strip()
        self.command_bar.clear()
        if command:
            self.execute_command(command)

    def execute_command(self, command):
        current_editor = self.tabs.currentWidget()
        if not isinstance(current_editor, EditorWithLines):
            return

        if command == ":dd":
            cursor = current_editor.textCursor()
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        elif command == ":w":
            self.sauvegarder_fichier()
        elif command == ":wq":
            self.sauvegarder_fichier()
            self.fermer_onglet(self.tabs.currentIndex())
        elif command == ":q":
            self.fermer_onglet(self.tabs.currentIndex())
        elif command.startswith(":gt"):
            try:
                line_number = int(command[3:])
                if line_number > 0:
                    block = current_editor.document().findBlockByNumber(line_number - 1)
                    if block.isValid():
                        cursor = current_editor.textCursor()
                        cursor.setPosition(block.position())
                        current_editor.setTextCursor(cursor)
                        current_editor.centerCursor()
            except ValueError:
                QMessageBox.warning(self, "Erreur", "Numéro de ligne invalide.")
        elif command == ":lint":
            if self.get_current_file_extension() == ".py":
                output = self.run_flake8(self.get_current_file_name())
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Résultats")
                msg_box.setIcon(QMessageBox.Icon.Information)
                text_edit = QTextEdit()
                text_edit.setPlainText(output)
                text_edit.setReadOnly(True)
                text_edit.setMinimumSize(600, 400)
                msg_box.layout().addWidget(text_edit)
                msg_box.exec()
            else:
                QMessageBox.warning(self, "Erreur", "Linting uniquement pris en charge pour les fichiers Python.")

    def run_flake8(self, file_path):
        disabled_rules = set()
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("# lint disable"):
                    parts = line.strip().split()
                    if len(parts) > 2:
                        disabled_rules.update(parts[2:])

        flake8_command = ["flake8", "--ignore=E501,E302,E305,E701", file_path]
        if disabled_rules:
            flake8_command.append(f"--ignore={','.join(disabled_rules)}")

        result = subprocess.run(flake8_command, capture_output=True, text=True)
        return result.stdout

    def get_current_file_name(self):
        current_index = self.tabs.currentIndex()
        if current_index != -1:
            return self.tab_data.get(current_index)
        return None

    def get_current_file_extension(self):
        current_editor = self.tabs.currentWidget()
        if isinstance(current_editor, EditorWithLines):
            return current_editor.get_file_extension()
        return None

    def ouvrir_fichier(self):
        chemin, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier", "")
        if chemin:
            self.ajouter_onglet(chemin)

    def ouvrir_dossier(self):
        dossier = QFileDialog.getExistingDirectory(self, "Ouvrir un dossier", "")
        if dossier:
            self.file_explorer.setRootIndex(self.file_model.index(dossier))

    def ouvrir_fichier_depuis_explorateur(self, index):
        chemin = self.file_model.filePath(index)
        if os.path.isfile(chemin):
            self.ajouter_onglet(chemin)

    def creer_fichier(self):
        chemin, _ = QFileDialog.getSaveFileName(self, "Créer un fichier", "", "Tous les fichiers (*)")
        if chemin:
            with open(chemin, 'w', encoding='utf-8') as f:
                pass
            self.ajouter_onglet(chemin)
            QMessageBox.information(self, "Fichier créé", f"Le fichier '{chemin}' a été créé avec succès.")

    def sauvegarder_fichier(self):
        current_index = self.tabs.currentIndex()
        if current_index != -1:
            chemin = self.tab_data.get(current_index)
            if chemin:
                editor = self.tabs.currentWidget()
                with open(chemin, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
                QMessageBox.information(self, "Sauvegarde", f"Fichier sauvegardé : {chemin}")
            else:
                QMessageBox.warning(self, "Erreur", "Chemin du fichier introuvable.")
        else:
            QMessageBox.warning(self, "Erreur", "Aucun fichier ouvert.")

    def ajouter_onglet(self, chemin):
        editor = EditorWithLines(self, self)
        with open(chemin, 'r', encoding='utf-8') as f:
            editor.setPlainText(f.read())
        file_extension = os.path.splitext(chemin)[1]
        editor.set_file_extension(file_extension)
        tab_index = self.tabs.addTab(editor, os.path.basename(chemin))
        self.tab_data[tab_index] = chemin

    def fermer_onglet(self, index):
        if index in self.tab_data:
            del self.tab_data[index]
        self.tabs.removeTab(index)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    fenetre = EditeurCode()
    fenetre.show()
    sys.exit(app.exec())
