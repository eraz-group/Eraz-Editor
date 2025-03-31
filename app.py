import sys
import os
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QPlainTextEdit,
    QTabWidget,
    QSplitter,
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QTreeView,
    QLineEdit
)
from PyQt6.QtCore import Qt, QDir, QRect
from PyQt6.QtGui import QFileSystemModel, QAction, QKeySequence, QPainter, QColor


class NumberBar(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.editor.blockCountChanged.connect(self.updateWidth)
        self.editor.updateRequest.connect(self.updateContents)
        self.updateWidth()

    def updateWidth(self):
        width = self.fontMetrics().horizontalAdvance(str(self.editor.blockCount())) + 20
        if self.width() != width:
            self.setFixedWidth(width)

    def updateContents(self, rect, dy):
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#2d2d30"))
        block = self.editor.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#858585"))
                painter.drawText(0, int(top), self.width() - 10, self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, str(blockNumber + 1))
            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            blockNumber += 1


class EditorWithLines(QPlainTextEdit):
    def __init__(self, parent, editor_code):
        super().__init__(parent)
        self.editor_code = editor_code  # Reference to the EditeurCode instance
        self.number_bar = NumberBar(self)
        self.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 14px; ")
        self.update_margins()
        self.command_mode = False

        # Add a QLineEdit for command input
        self.command_input = QLineEdit(self)
        self.command_input.setPlaceholderText("Enter command")
        self.command_input.setStyleSheet("background-color: #252526; color: #dcdcdc; border: none; padding: 5px;")
        self.command_input.hide()  # Initially hidden
        self.command_input.returnPressed.connect(self.execute_command_from_input)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.number_bar.setGeometry(QRect(cr.left(), cr.top(), self.number_bar.width(), cr.height()))
        self.update_margins()

        # Position the command input at the bottom of the editor
        self.command_input.setGeometry(0, self.height() - 30, self.width(), 30)

    def update_margins(self):
        self.setViewportMargins(self.number_bar.width(), 0, 0, 0)

    def keyPressEvent(self, event):
        if self.command_mode:
            if event.key() == Qt.Key.Key_Escape:  # Exit command mode
                self.command_mode = False
                self.command_input.hide()
            else:
                super().keyPressEvent(event)
        else:
            if event.key() == Qt.Key.Key_Escape:  # Enter command mode
                self.command_mode = True
                self.command_input.show()
                self.command_input.setFocus()
            else:
                super().keyPressEvent(event)

    def execute_command_from_input(self):
        command = self.command_input.text()
        self.command_input.clear()
        self.command_input.hide()
        self.command_mode = False
        self.editor_code.execute_command(command)  # Use the reference to call execute_command


class EditeurCode(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eraz Editor Professional")
        self.setGeometry(100, 100, 1400, 900)

        self.setStyleSheet("background-color: #2d2d30; color: #dcdcdc;")

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)
        self.splitter.setSizes([250, 1150])

        # File explorer using QTreeView and QFileSystemModel
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")  # Set the root path to the file system
        self.file_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.file_explorer = QTreeView()
        self.file_explorer.setModel(self.file_model)
        self.file_explorer.setRootIndex(self.file_model.index(""))  # Set the initial directory
        self.file_explorer.setStyleSheet("background-color: #252526; color: #dcdcdc;")
        self.file_explorer.doubleClicked.connect(self.ouvrir_fichier_depuis_explorateur)
        self.splitter.addWidget(self.file_explorer)

        right_widget = QWidget()
        right_layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.fermer_onglet)
        right_layout.addWidget(self.tabs)

        right_widget.setLayout(right_layout)
        self.splitter.addWidget(right_widget)

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

    def execute_command(self, command):
        current_editor = self.tabs.currentWidget()
        if not isinstance(current_editor, EditorWithLines):
            return

        if command == ":dd":  # Delete current line
            cursor = current_editor.textCursor()
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        elif command == ":w":  # Save file
            self.sauvegarder_fichier()
        elif command == ":wq":  # Save and close
            self.sauvegarder_fichier()
            self.fermer_onglet(self.tabs.currentIndex())
        elif command == ":q":  # Close tab
            self.fermer_onglet(self.tabs.currentIndex())

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
            # Create an empty file
            with open(chemin, 'w', encoding='utf-8') as f:
                pass
            # Open the new file in a tab
            self.ajouter_onglet(chemin)
            QMessageBox.information(self, "Fichier créé", f"Le fichier '{chemin}' a été créé avec succès.")

    def sauvegarder_fichier(self):
        editor = self.tabs.currentWidget()
        if editor:
            chemin = os.path.join(self.dossier_actuel, self.tabs.tabText(self.tabs.currentIndex()))
            with open(chemin, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            QMessageBox.information(self, "Sauvegarde", "Fichier sauvegardé")

    def ajouter_onglet(self, chemin):
        editor = EditorWithLines(self, self)  # Pass self as both parent and editor_code
        with open(chemin, 'r', encoding='utf-8') as f:
            editor.setPlainText(f.read())
        self.tabs.addTab(editor, os.path.basename(chemin))

    def fermer_onglet(self, index):
        self.tabs.removeTab(index)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    fenetre = EditeurCode()
    fenetre.show()
    sys.exit(app.exec())