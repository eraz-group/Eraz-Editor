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
    QTreeView
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
    def __init__(self):
        super().__init__()
        self.number_bar = NumberBar(self)
        self.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 14px; ")
        self.update_margins()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.number_bar.setGeometry(QRect(cr.left(), cr.top(), self.number_bar.width(), cr.height()))
        self.update_margins()

    def update_margins(self):
        self.setViewportMargins(self.number_bar.width(), 0, 0, 0)


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

        sauvegarder_action = QAction("Sauvegarder fichier", self)
        sauvegarder_action.setShortcut(QKeySequence("Ctrl+S"))
        sauvegarder_action.triggered.connect(self.sauvegarder_fichier)
        fichier_menu.addAction(sauvegarder_action)

        self.dossier_actuel = ""

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

    def sauvegarder_fichier(self):
        editor = self.tabs.currentWidget()
        if editor:
            chemin = os.path.join(self.dossier_actuel, self.tabs.tabText(self.tabs.currentIndex()))
            with open(chemin, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            QMessageBox.information(self, "Sauvegarde", "Fichier sauvegardé")

    def ajouter_onglet(self, chemin):
        editor = EditorWithLines()
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