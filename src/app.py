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
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

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

        annuler_action = QAction("Annuler", self)
        annuler_action.setShortcut(QKeySequence("Ctrl+Z"))
        annuler_action.triggered.connect(self.annuler_action)
        fichier_menu.addAction(annuler_action)

        refaire_action = QAction("Refaire", self)
        refaire_action.setShortcut(QKeySequence("Ctrl+Y"))
        refaire_action.triggered.connect(self.refaire_action)
        fichier_menu.addAction(refaire_action)

        self.dossier_actuel = ""

        self.setStyleSheet("""
            QMainWindow { background-color: #2d2d30; }
            QListWidget { background-color: #1e1e1e; color: #dcdcdc; }
            QTextEdit { background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas; font-size: 14px; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #333; color: #dcdcdc; padding: 10px; }
            QTabBar::tab:selected { background: #007acc; color: #ffffff; }
        """)

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
        if widget_actuel:
            index = self.tabs.currentIndex()
            nom_fichier = self.tabs.tabText(index)
            chemin = os.path.join(self.dossier_actuel, nom_fichier)
            with open(chemin, 'w', encoding='utf-8') as fichier:
                fichier.write(widget_actuel.toPlainText())
            QMessageBox.information(self, "Sauvegarde", f"Le fichier {nom_fichier} a été sauvegardé avec succès !")
        else:
            QMessageBox.warning(self, "Erreur", "Aucun fichier ouvert à sauvegarder.")

    def ajouter_onglet(self, chemin):
        with open(chemin, 'r', encoding='utf-8') as fichier:
            contenu = fichier.read()
            editeur = QTextEdit()
            editeur.setPlainText(contenu)
            nom_fichier = os.path.basename(chemin)
            self.tabs.addTab(editeur, nom_fichier)

    def fermer_onglet(self, index):
        self.tabs.removeTab(index)

    def annuler_action(self):
        if self.tabs.currentWidget():
            self.tabs.currentWidget().undo()

    def refaire_action(self):
        if self.tabs.currentWidget():
            self.tabs.currentWidget().redo()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    fenetre = EditeurCode()
    fenetre.show()
    sys.exit(app.exec())