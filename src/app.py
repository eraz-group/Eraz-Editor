import sys
import os
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QTextEdit,
    QMenuBar,
    QTabWidget,
    QSplitter,
    QListWidget,
    QMessageBox,
    QWidget,
    QPlainTextEdit,
    QLineEdit
)
from PyQt6.QtCore import Qt, QFileSystemWatcher, QRect, QEvent
from PyQt6.QtGui import QAction, QKeySequence, QPainter, QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView  # Import for HTML previewer


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
        # Set the viewport margins to make space for the number bar
        self.setViewportMargins(self.number_bar.width(), 0, 0, 0)

class EditeurCode(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eraz Editor Professionnal")
        self.setGeometry(100, 100, 1200, 800)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)
        self.splitter.setSizes([250, 950])

        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(self.ouvrir_fichier_depuis_liste)
        self.splitter.addWidget(self.file_list)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.fermer_onglet)
        self.splitter.addWidget(self.tabs)

        self.menu = QMenuBar()
        self.setMenuBar(self.menu)

        fichier_menu = self.menu.addMenu("Fichier")

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

        afficher_html_action = QAction("Afficher HTML", self)
        afficher_html_action.setShortcut(QKeySequence("Ctrl+H"))
        afficher_html_action.triggered.connect(self.afficher_html)
        fichier_menu.addAction(afficher_html_action)

        self.dossier_actuel = ""
        self.file_watcher = QFileSystemWatcher()  # Initialize file watcher
        self.file_watcher.fileChanged.connect(self.recharger_html)  # Connect to reload method

        self.tab_file_paths = {}  # Dictionary to store file paths for each tab

        self.setStyleSheet("""
            QMainWindow { background-color: #2d2d30; }
            QListWidget { background-color: #1e1e1e; color: #dcdcdc; }
            QTextEdit { background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 14px; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #dcdcdc; padding: 10px; }
            QTabBar::tab:selected { background: #007acc; color: #ffffff; }
        """)

        # Initialize the command bar
        self.command_bar = QLineEdit(self)
        self.command_bar.setPlaceholderText("Enter command (e.g., :wq)")
        self.command_bar.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 14px; padding: 5px;")
        self.command_bar.hide()  # Hide the command bar initially
        self.command_bar.returnPressed.connect(self.execute_command)  # Connect to command execution
        self.command_bar.installEventFilter(self)  # Install event filter to handle Esc key

        # Shortcut to activate the command bar
        self.command_shortcut = QAction(self)
        self.command_shortcut.setShortcut(QKeySequence("Esc"))
        self.command_shortcut.triggered.connect(self.show_command_bar)
        self.addAction(self.command_shortcut)

    def show_command_bar(self):
        if not self.command_bar.isVisible():
            self.command_bar.setGeometry(0, self.height() - 30, self.width(), 30)  # Position at the bottom
            self.command_bar.show()
            self.command_bar.setFocus()
        else:
            self.command_bar.hide()


    def execute_command(self):
        command = self.command_bar.text().strip()
        if command == ":wq":
            self.sauvegarder_fichier()  # Save the current file
            self.close()  # Quit the application
        elif command == ":q":
            self.close()  # Quit the application without saving
        elif command == ":w":
            self.sauvegarder_fichier()  # Save the current file
        else:
            QMessageBox.warning(self, "Commande inconnue", f"Commande non reconnue: {command}")
        self.command_bar.clear()
        self.command_bar.hide()

    def ouvrir_fichier(self):
        chemin, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier", "", "Tous les fichiers (*);;Python (*.py);;HTML (*.html)")
        if chemin:
            self.ajouter_onglet(chemin)

    def ouvrir_dossier(self):
        dossier = QFileDialog.getExistingDirectory(self, "Ouvrir un dossier", "")
        if dossier:
            self.dossier_actuel = dossier
            self.file_list.clear()
            for root, dirs, files in os.walk(dossier):
                for nom in files:
                    chemin_fichier = os.path.relpath(os.path.join(root, nom), dossier)
                    self.file_list.addItem(chemin_fichier)

    def ouvrir_fichier_depuis_liste(self, item):
        chemin = os.path.join(self.dossier_actuel, item.text())
        if os.path.isfile(chemin):
            self.ajouter_onglet(chemin)

    def sauvegarder_fichier(self):
        widget_actuel = self.tabs.currentWidget()
        if widget_actuel and isinstance(widget_actuel, QTextEdit):
            index = self.tabs.indexOf(widget_actuel)  # Get the current tab index
            chemin = self.tab_file_paths.get(index)  # Retrieve the full file path for the current tab
            if chemin:
                try:
                    with open(chemin, 'w', encoding='utf-8') as fichier:
                        fichier.write(widget_actuel.toPlainText())
                    QMessageBox.information(self, "Sauvegarde", f"Le fichier {chemin} a été sauvegardé avec succès !")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Une erreur s'est produite lors de la sauvegarde : {e}")
            else:
                QMessageBox.warning(self, "Erreur", "Chemin du fichier introuvable. Assurez-vous que le fichier a été ouvert correctement.")
        else:
            QMessageBox.warning(self, "Erreur", "Aucun fichier texte ouvert à sauvegarder.")

    def ajouter_onglet(self, chemin):
        with open(chemin, 'r', encoding='utf-8') as fichier:
            contenu = fichier.read()
            editeur = EditorWithLines()  # Use EditorWithLines instead of QTextEdit
            editeur.setPlainText(contenu)
            nom_fichier = os.path.basename(chemin)
            index = self.tabs.addTab(editeur, nom_fichier)
            self.tab_file_paths[index] = chemin  # Store the full file path for the new tab

    def fermer_onglet(self, index):
        if index in self.tab_file_paths:
            del self.tab_file_paths[index]  # Remove the file path from the dictionary
        self.tabs.removeTab(index)

    def afficher_html(self):
        chemin, _ = QFileDialog.getOpenFileName(self, "Sélectionner un fichier HTML", "", "HTML (*.html)")
        if chemin:
            vue_html = QWebEngineView()
            vue_html.setHtml(open(chemin, 'r', encoding='utf-8').read())
            index = self.tabs.addTab(vue_html, f"Aperçu: {os.path.basename(chemin)}")
            self.tabs.setCurrentWidget(vue_html)
            self.file_watcher.addPath(chemin)  # Add file to watcher

    def recharger_html(self, chemin):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, QWebEngineView):
                widget.setHtml(open(chemin, 'r', encoding='utf-8').read())
                break

if __name__ == '__main__':
    app = QApplication(sys.argv)
    fenetre = EditeurCode()
    fenetre.show()
    sys.exit(app.exec())