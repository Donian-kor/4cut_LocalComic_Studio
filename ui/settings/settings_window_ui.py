# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget)
class Ui_SettingsWindow(object):
    def setupUi(self, SettingsWindow):
        if not SettingsWindow.objectName():
            SettingsWindow.setObjectName(u"SettingsWindow")
        SettingsWindow.setMinimumSize(QSize(650, 500))
        self.verticalLayout = QVBoxLayout(SettingsWindow)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabs = QTabWidget(SettingsWindow)
        self.tabs.setObjectName(u"tabs")
        self.lmstudioTab = QWidget()
        self.lmstudioTab.setObjectName(u"lmstudioTab")
        self.lmForm = QFormLayout(self.lmstudioTab)
        self.lmForm.setObjectName(u"lmForm")
        self.lmHostLabel = QLabel(self.lmstudioTab)
        self.lmHostLabel.setObjectName(u"lmHostLabel")

        self.lmForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lmHostLabel)

        self.lmHostEdit = QLineEdit(self.lmstudioTab)
        self.lmHostEdit.setObjectName(u"lmHostEdit")

        self.lmForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lmHostEdit)

        self.lmPortLabel = QLabel(self.lmstudioTab)
        self.lmPortLabel.setObjectName(u"lmPortLabel")

        self.lmForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lmPortLabel)

        self.lmPortSpin = QSpinBox(self.lmstudioTab)
        self.lmPortSpin.setObjectName(u"lmPortSpin")
        self.lmPortSpin.setMaximum(65535)

        self.lmForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.lmPortSpin)

        self.lmApiLabel = QLabel(self.lmstudioTab)
        self.lmApiLabel.setObjectName(u"lmApiLabel")

        self.lmForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lmApiLabel)

        self.lmApiEdit = QLineEdit(self.lmstudioTab)
        self.lmApiEdit.setObjectName(u"lmApiEdit")

        self.lmForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lmApiEdit)

        self.lmModelLabel = QLabel(self.lmstudioTab)
        self.lmModelLabel.setObjectName(u"lmModelLabel")

        self.lmForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lmModelLabel)

        self.lmModelCombo = QComboBox(self.lmstudioTab)
        self.lmModelCombo.setObjectName(u"lmModelCombo")
        self.lmModelCombo.setEditable(True)

        self.lmForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.lmModelCombo)

        self.lmTestButton = QPushButton(self.lmstudioTab)
        self.lmTestButton.setObjectName(u"lmTestButton")

        self.lmForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.lmTestButton)

        self.lmStatusLabel = QLabel(self.lmstudioTab)
        self.lmStatusLabel.setObjectName(u"lmStatusLabel")

        self.lmForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.lmStatusLabel)

        self.tabs.addTab(self.lmstudioTab, "")
        self.comfyTab = QWidget()
        self.comfyTab.setObjectName(u"comfyTab")
        self.comfyForm = QFormLayout(self.comfyTab)
        self.comfyForm.setObjectName(u"comfyForm")
        self.comfyHostLabel = QLabel(self.comfyTab)
        self.comfyHostLabel.setObjectName(u"comfyHostLabel")

        self.comfyForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.comfyHostLabel)

        self.comfyHostEdit = QLineEdit(self.comfyTab)
        self.comfyHostEdit.setObjectName(u"comfyHostEdit")

        self.comfyForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comfyHostEdit)

        self.comfyPortLabel = QLabel(self.comfyTab)
        self.comfyPortLabel.setObjectName(u"comfyPortLabel")

        self.comfyForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.comfyPortLabel)

        self.comfyPortSpin = QSpinBox(self.comfyTab)
        self.comfyPortSpin.setObjectName(u"comfyPortSpin")
        self.comfyPortSpin.setMaximum(65535)

        self.comfyForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comfyPortSpin)

        self.comfyWorkflowLabel = QLabel(self.comfyTab)
        self.comfyWorkflowLabel.setObjectName(u"comfyWorkflowLabel")

        self.comfyForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.comfyWorkflowLabel)

        self.workflowLayout = QHBoxLayout()
        self.workflowLayout.setObjectName(u"workflowLayout")
        self.comfyWorkflowEdit = QLineEdit(self.comfyTab)
        self.comfyWorkflowEdit.setObjectName(u"comfyWorkflowEdit")

        self.workflowLayout.addWidget(self.comfyWorkflowEdit)

        self.browseWorkflowButton = QPushButton(self.comfyTab)
        self.browseWorkflowButton.setObjectName(u"browseWorkflowButton")

        self.workflowLayout.addWidget(self.browseWorkflowButton)


        self.comfyForm.setLayout(2, QFormLayout.ItemRole.FieldRole, self.workflowLayout)

        self.comfyTestButton = QPushButton(self.comfyTab)
        self.comfyTestButton.setObjectName(u"comfyTestButton")

        self.comfyForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.comfyTestButton)

        self.comfyStatusLabel = QLabel(self.comfyTab)
        self.comfyStatusLabel.setObjectName(u"comfyStatusLabel")

        self.comfyForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.comfyStatusLabel)

        self.tabs.addTab(self.comfyTab, "")
        self.generalTab = QWidget()
        self.generalTab.setObjectName(u"generalTab")
        self.generalForm = QFormLayout(self.generalTab)
        self.generalForm.setObjectName(u"generalForm")
        self.label = QLabel(self.generalTab)
        self.label.setObjectName(u"label")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label)

        self.projectPathEdit = QLineEdit(self.generalTab)
        self.projectPathEdit.setObjectName(u"projectPathEdit")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.projectPathEdit)

        self.label1 = QLabel(self.generalTab)
        self.label1.setObjectName(u"label1")

        self.generalForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label1)

        self.widthSpin = QSpinBox(self.generalTab)
        self.widthSpin.setObjectName(u"widthSpin")
        self.widthSpin.setMaximum(4096)

        self.generalForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.widthSpin)

        self.label2 = QLabel(self.generalTab)
        self.label2.setObjectName(u"label2")

        self.generalForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label2)

        self.heightSpin = QSpinBox(self.generalTab)
        self.heightSpin.setObjectName(u"heightSpin")
        self.heightSpin.setMaximum(4096)

        self.generalForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.heightSpin)

        self.autoSaveCheck = QCheckBox(self.generalTab)
        self.autoSaveCheck.setObjectName(u"autoSaveCheck")

        self.generalForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.autoSaveCheck)

        self.tabs.addTab(self.generalTab, "")

        self.verticalLayout.addWidget(self.tabs)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setObjectName(u"buttonLayout")
        self.buttonSpacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonLayout.addItem(self.buttonSpacer)

        self.cancelButton = QPushButton(SettingsWindow)
        self.cancelButton.setObjectName(u"cancelButton")

        self.buttonLayout.addWidget(self.cancelButton)

        self.applyButton = QPushButton(SettingsWindow)
        self.applyButton.setObjectName(u"applyButton")

        self.buttonLayout.addWidget(self.applyButton)


        self.verticalLayout.addLayout(self.buttonLayout)


        self.retranslateUi(SettingsWindow)

        QMetaObject.connectSlotsByName(SettingsWindow)
    # setupUi

    def retranslateUi(self, SettingsWindow):
        SettingsWindow.setWindowTitle(QCoreApplication.translate("SettingsWindow", u"4Cut Local - AI \uc5f0\uacb0 \uc124\uc815", None))
        self.lmHostLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc11c\ubc84 \uc8fc\uc18c", None))
        self.lmPortLabel.setText(QCoreApplication.translate("SettingsWindow", u"\ud3ec\ud2b8", None))
        self.lmApiLabel.setText(QCoreApplication.translate("SettingsWindow", u"API \uacbd\ub85c", None))
        self.lmModelLabel.setText(QCoreApplication.translate("SettingsWindow", u"\ubaa8\ub378", None))
        self.lmTestButton.setText(QCoreApplication.translate("SettingsWindow", u"\uc5f0\uacb0 \ud14c\uc2a4\ud2b8", None))
        self.lmStatusLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc0c1\ud0dc: \ud14c\uc2a4\ud2b8 \uc804", None))
        self.tabs.setTabText(self.tabs.indexOf(self.lmstudioTab), QCoreApplication.translate("SettingsWindow", u"LM Studio", None))
        self.comfyHostLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc11c\ubc84 \uc8fc\uc18c", None))
        self.comfyPortLabel.setText(QCoreApplication.translate("SettingsWindow", u"\ud3ec\ud2b8", None))
        self.comfyWorkflowLabel.setText(QCoreApplication.translate("SettingsWindow", u"Workflow", None))
        self.browseWorkflowButton.setText(QCoreApplication.translate("SettingsWindow", u"\ucc3e\uc544\ubcf4\uae30", None))
        self.comfyTestButton.setText(QCoreApplication.translate("SettingsWindow", u"\uc5f0\uacb0 \ud14c\uc2a4\ud2b8", None))
        self.comfyStatusLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc0c1\ud0dc: \ud14c\uc2a4\ud2b8 \uc804", None))
        self.tabs.setTabText(self.tabs.indexOf(self.comfyTab), QCoreApplication.translate("SettingsWindow", u"ComfyUI", None))
        self.label.setText(QCoreApplication.translate("SettingsWindow", u"\ud504\ub85c\uc81d\ud2b8 \uc800\uc7a5 \uc704\uce58", None))
        self.label1.setText(QCoreApplication.translate("SettingsWindow", u"\uc774\ubbf8\uc9c0 \ub108\ube44", None))
        self.label2.setText(QCoreApplication.translate("SettingsWindow", u"\uc774\ubbf8\uc9c0 \ub192\uc774", None))
        self.autoSaveCheck.setText(QCoreApplication.translate("SettingsWindow", u"\uacb0\uacfc \uc790\ub3d9 \uc800\uc7a5", None))
        self.tabs.setTabText(self.tabs.indexOf(self.generalTab), QCoreApplication.translate("SettingsWindow", u"\uc77c\ubc18", None))
        self.cancelButton.setText(QCoreApplication.translate("SettingsWindow", u"\ucde8\uc18c", None))
        self.applyButton.setText(QCoreApplication.translate("SettingsWindow", u"\uc801\uc6a9", None))
    # retranslateUi

