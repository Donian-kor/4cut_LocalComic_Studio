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
    QDoubleSpinBox, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget)

class Ui_SettingsWindow(object):
    def setupUi(self, SettingsWindow):
        if not SettingsWindow.objectName():
            SettingsWindow.setObjectName(u"SettingsWindow")
        SettingsWindow.resize(700, 666)
        SettingsWindow.setMinimumSize(QSize(700, 620))
        self.verticalLayout = QVBoxLayout(SettingsWindow)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabs = QTabWidget(SettingsWindow)
        self.tabs.setObjectName(u"tabs")
        self.aiServerTab = QWidget()
        self.aiServerTab.setObjectName(u"aiServerTab")
        self.aiServerLayout = QVBoxLayout(self.aiServerTab)
        self.aiServerLayout.setObjectName(u"aiServerLayout")
        self.lmGroup = QGroupBox(self.aiServerTab)
        self.lmGroup.setObjectName(u"lmGroup")
        self.lmForm = QFormLayout(self.lmGroup)
        self.lmForm.setObjectName(u"lmForm")
        self.lmHostLabel = QLabel(self.lmGroup)
        self.lmHostLabel.setObjectName(u"lmHostLabel")

        self.lmForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lmHostLabel)

        self.lmHostEdit = QLineEdit(self.lmGroup)
        self.lmHostEdit.setObjectName(u"lmHostEdit")

        self.lmForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lmHostEdit)

        self.lmPortLabel = QLabel(self.lmGroup)
        self.lmPortLabel.setObjectName(u"lmPortLabel")

        self.lmForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lmPortLabel)

        self.lmPortSpin = QSpinBox(self.lmGroup)
        self.lmPortSpin.setObjectName(u"lmPortSpin")
        self.lmPortSpin.setMaximum(65535)

        self.lmForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.lmPortSpin)

        self.lmApiLabel = QLabel(self.lmGroup)
        self.lmApiLabel.setObjectName(u"lmApiLabel")

        self.lmForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lmApiLabel)

        self.lmApiEdit = QLineEdit(self.lmGroup)
        self.lmApiEdit.setObjectName(u"lmApiEdit")

        self.lmForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lmApiEdit)

        self.lmModelLabel = QLabel(self.lmGroup)
        self.lmModelLabel.setObjectName(u"lmModelLabel")

        self.lmForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lmModelLabel)

        self.lmModelCombo = QComboBox(self.lmGroup)
        self.lmModelCombo.setObjectName(u"lmModelCombo")
        self.lmModelCombo.setEditable(True)

        self.lmForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.lmModelCombo)

        self.lmTestButton = QPushButton(self.lmGroup)
        self.lmTestButton.setObjectName(u"lmTestButton")

        self.lmForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.lmTestButton)

        self.lmStatusLabel = QLabel(self.lmGroup)
        self.lmStatusLabel.setObjectName(u"lmStatusLabel")

        self.lmForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.lmStatusLabel)


        self.aiServerLayout.addWidget(self.lmGroup)

        self.serverDivider = QFrame(self.aiServerTab)
        self.serverDivider.setObjectName(u"serverDivider")
        self.serverDivider.setFrameShape(QFrame.Shape.HLine)
        self.serverDivider.setFrameShadow(QFrame.Shadow.Sunken)

        self.aiServerLayout.addWidget(self.serverDivider)

        self.comfyGroup = QGroupBox(self.aiServerTab)
        self.comfyGroup.setObjectName(u"comfyGroup")
        self.comfyForm = QFormLayout(self.comfyGroup)
        self.comfyForm.setObjectName(u"comfyForm")
        self.comfyHostLabel = QLabel(self.comfyGroup)
        self.comfyHostLabel.setObjectName(u"comfyHostLabel")

        self.comfyForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.comfyHostLabel)

        self.comfyHostEdit = QLineEdit(self.comfyGroup)
        self.comfyHostEdit.setObjectName(u"comfyHostEdit")

        self.comfyForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comfyHostEdit)

        self.comfyPortLabel = QLabel(self.comfyGroup)
        self.comfyPortLabel.setObjectName(u"comfyPortLabel")

        self.comfyForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.comfyPortLabel)

        self.comfyPortSpin = QSpinBox(self.comfyGroup)
        self.comfyPortSpin.setObjectName(u"comfyPortSpin")
        self.comfyPortSpin.setMaximum(65535)

        self.comfyForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comfyPortSpin)

        self.comfyWorkflowLabel = QLabel(self.comfyGroup)
        self.comfyWorkflowLabel.setObjectName(u"comfyWorkflowLabel")

        self.comfyForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.comfyWorkflowLabel)

        self.workflowLayout = QHBoxLayout()
        self.workflowLayout.setObjectName(u"workflowLayout")
        self.comfyWorkflowEdit = QLineEdit(self.comfyGroup)
        self.comfyWorkflowEdit.setObjectName(u"comfyWorkflowEdit")

        self.workflowLayout.addWidget(self.comfyWorkflowEdit)

        self.browseWorkflowButton = QPushButton(self.comfyGroup)
        self.browseWorkflowButton.setObjectName(u"browseWorkflowButton")

        self.workflowLayout.addWidget(self.browseWorkflowButton)


        self.comfyForm.setLayout(2, QFormLayout.ItemRole.FieldRole, self.workflowLayout)

        self.comfyTestButton = QPushButton(self.comfyGroup)
        self.comfyTestButton.setObjectName(u"comfyTestButton")

        self.comfyForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.comfyTestButton)

        self.comfyStatusLabel = QLabel(self.comfyGroup)
        self.comfyStatusLabel.setObjectName(u"comfyStatusLabel")

        self.comfyForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.comfyStatusLabel)


        self.aiServerLayout.addWidget(self.comfyGroup)

        self.serverSpacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.aiServerLayout.addItem(self.serverSpacer)

        self.tabs.addTab(self.aiServerTab, "")
        self.imageModelTab = QWidget()
        self.imageModelTab.setObjectName(u"imageModelTab")
        self.imageModelMainLayout = QHBoxLayout(self.imageModelTab)
        self.imageModelMainLayout.setObjectName(u"imageModelMainLayout")
        self.imageModelListLayout = QVBoxLayout()
        self.imageModelListLayout.setObjectName(u"imageModelListLayout")
        self.imageModelListLabel = QLabel(self.imageModelTab)
        self.imageModelListLabel.setObjectName(u"imageModelListLabel")

        self.imageModelListLayout.addWidget(self.imageModelListLabel)

        self.imageModelList = QListWidget(self.imageModelTab)
        self.imageModelList.setObjectName(u"imageModelList")

        self.imageModelListLayout.addWidget(self.imageModelList)

        self.imageModelButtonLayout = QHBoxLayout()
        self.imageModelButtonLayout.setObjectName(u"imageModelButtonLayout")
        self.addImageModelButton = QPushButton(self.imageModelTab)
        self.addImageModelButton.setObjectName(u"addImageModelButton")

        self.imageModelButtonLayout.addWidget(self.addImageModelButton)

        self.removeImageModelButton = QPushButton(self.imageModelTab)
        self.removeImageModelButton.setObjectName(u"removeImageModelButton")

        self.imageModelButtonLayout.addWidget(self.removeImageModelButton)


        self.imageModelListLayout.addLayout(self.imageModelButtonLayout)


        self.imageModelMainLayout.addLayout(self.imageModelListLayout)

        self.imageModelForm = QFormLayout()
        self.imageModelForm.setObjectName(u"imageModelForm")
        self.label = QLabel(self.imageModelTab)
        self.label.setObjectName(u"label")

        self.imageModelForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label)

        self.imageModelNameEdit = QLineEdit(self.imageModelTab)
        self.imageModelNameEdit.setObjectName(u"imageModelNameEdit")

        self.imageModelForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.imageModelNameEdit)

        self.label1 = QLabel(self.imageModelTab)
        self.label1.setObjectName(u"label1")

        self.imageModelForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label1)

        self.imageModelFileLayout = QHBoxLayout()
        self.imageModelFileLayout.setObjectName(u"imageModelFileLayout")
        self.imageModelFileEdit = QLineEdit(self.imageModelTab)
        self.imageModelFileEdit.setObjectName(u"imageModelFileEdit")

        self.imageModelFileLayout.addWidget(self.imageModelFileEdit)

        self.browseImageModelButton = QPushButton(self.imageModelTab)
        self.browseImageModelButton.setObjectName(u"browseImageModelButton")

        self.imageModelFileLayout.addWidget(self.browseImageModelButton)


        self.imageModelForm.setLayout(1, QFormLayout.ItemRole.FieldRole, self.imageModelFileLayout)

        self.label2 = QLabel(self.imageModelTab)
        self.label2.setObjectName(u"label2")

        self.imageModelForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label2)

        self.imageModelWorkflowLayout = QHBoxLayout()
        self.imageModelWorkflowLayout.setObjectName(u"imageModelWorkflowLayout")
        self.imageModelWorkflowEdit = QLineEdit(self.imageModelTab)
        self.imageModelWorkflowEdit.setObjectName(u"imageModelWorkflowEdit")

        self.imageModelWorkflowLayout.addWidget(self.imageModelWorkflowEdit)

        self.browseImageModelWorkflowButton = QPushButton(self.imageModelTab)
        self.browseImageModelWorkflowButton.setObjectName(u"browseImageModelWorkflowButton")

        self.imageModelWorkflowLayout.addWidget(self.browseImageModelWorkflowButton)


        self.imageModelForm.setLayout(2, QFormLayout.ItemRole.FieldRole, self.imageModelWorkflowLayout)

        self.label3 = QLabel(self.imageModelTab)
        self.label3.setObjectName(u"label3")

        self.imageModelForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label3)

        self.imageModelWidthSpin = QSpinBox(self.imageModelTab)
        self.imageModelWidthSpin.setObjectName(u"imageModelWidthSpin")
        self.imageModelWidthSpin.setMinimum(64)
        self.imageModelWidthSpin.setMaximum(4096)

        self.imageModelForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.imageModelWidthSpin)

        self.label4 = QLabel(self.imageModelTab)
        self.label4.setObjectName(u"label4")

        self.imageModelForm.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label4)

        self.imageModelHeightSpin = QSpinBox(self.imageModelTab)
        self.imageModelHeightSpin.setObjectName(u"imageModelHeightSpin")
        self.imageModelHeightSpin.setMinimum(64)
        self.imageModelHeightSpin.setMaximum(4096)

        self.imageModelForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.imageModelHeightSpin)

        self.label5 = QLabel(self.imageModelTab)
        self.label5.setObjectName(u"label5")

        self.imageModelForm.setWidget(5, QFormLayout.ItemRole.LabelRole, self.label5)

        self.imageModelStepsSpin = QSpinBox(self.imageModelTab)
        self.imageModelStepsSpin.setObjectName(u"imageModelStepsSpin")
        self.imageModelStepsSpin.setMinimum(1)
        self.imageModelStepsSpin.setMaximum(200)

        self.imageModelForm.setWidget(5, QFormLayout.ItemRole.FieldRole, self.imageModelStepsSpin)

        self.label6 = QLabel(self.imageModelTab)
        self.label6.setObjectName(u"label6")

        self.imageModelForm.setWidget(6, QFormLayout.ItemRole.LabelRole, self.label6)

        self.imageModelCfgSpin = QDoubleSpinBox(self.imageModelTab)
        self.imageModelCfgSpin.setObjectName(u"imageModelCfgSpin")
        self.imageModelCfgSpin.setDecimals(2)
        self.imageModelCfgSpin.setMaximum(30.000000000000000)
        self.imageModelCfgSpin.setSingleStep(0.500000000000000)

        self.imageModelForm.setWidget(6, QFormLayout.ItemRole.FieldRole, self.imageModelCfgSpin)

        self.label7 = QLabel(self.imageModelTab)
        self.label7.setObjectName(u"label7")

        self.imageModelForm.setWidget(7, QFormLayout.ItemRole.LabelRole, self.label7)

        self.imageModelSamplerCombo = QComboBox(self.imageModelTab)
        self.imageModelSamplerCombo.setObjectName(u"imageModelSamplerCombo")
        self.imageModelSamplerCombo.setEditable(True)

        self.imageModelForm.setWidget(7, QFormLayout.ItemRole.FieldRole, self.imageModelSamplerCombo)

        self.label8 = QLabel(self.imageModelTab)
        self.label8.setObjectName(u"label8")

        self.imageModelForm.setWidget(8, QFormLayout.ItemRole.LabelRole, self.label8)

        self.imageModelSchedulerCombo = QComboBox(self.imageModelTab)
        self.imageModelSchedulerCombo.setObjectName(u"imageModelSchedulerCombo")
        self.imageModelSchedulerCombo.setEditable(True)

        self.imageModelForm.setWidget(8, QFormLayout.ItemRole.FieldRole, self.imageModelSchedulerCombo)

        self.label9 = QLabel(self.imageModelTab)
        self.label9.setObjectName(u"label9")

        self.imageModelForm.setWidget(9, QFormLayout.ItemRole.LabelRole, self.label9)

        self.imageModelNegativeEdit = QPlainTextEdit(self.imageModelTab)
        self.imageModelNegativeEdit.setObjectName(u"imageModelNegativeEdit")

        self.imageModelForm.setWidget(9, QFormLayout.ItemRole.FieldRole, self.imageModelNegativeEdit)

        self.saveImageModelButton = QPushButton(self.imageModelTab)
        self.saveImageModelButton.setObjectName(u"saveImageModelButton")

        self.imageModelForm.setWidget(10, QFormLayout.ItemRole.FieldRole, self.saveImageModelButton)


        self.imageModelMainLayout.addLayout(self.imageModelForm)

        self.tabs.addTab(self.imageModelTab, "")
        self.generalTab = QWidget()
        self.generalTab.setObjectName(u"generalTab")
        self.generalForm = QFormLayout(self.generalTab)
        self.generalForm.setObjectName(u"generalForm")
        self.label10 = QLabel(self.generalTab)
        self.label10.setObjectName(u"label10")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label10)

        self.projectPathEdit = QLineEdit(self.generalTab)
        self.projectPathEdit.setObjectName(u"projectPathEdit")

        self.generalForm.setWidget(0, QFormLayout.ItemRole.FieldRole, self.projectPathEdit)

        self.label11 = QLabel(self.generalTab)
        self.label11.setObjectName(u"label11")

        self.generalForm.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label11)

        self.widthSpin = QSpinBox(self.generalTab)
        self.widthSpin.setObjectName(u"widthSpin")
        self.widthSpin.setMaximum(4096)

        self.generalForm.setWidget(1, QFormLayout.ItemRole.FieldRole, self.widthSpin)

        self.label12 = QLabel(self.generalTab)
        self.label12.setObjectName(u"label12")

        self.generalForm.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label12)

        self.heightSpin = QSpinBox(self.generalTab)
        self.heightSpin.setObjectName(u"heightSpin")
        self.heightSpin.setMaximum(4096)

        self.generalForm.setWidget(2, QFormLayout.ItemRole.FieldRole, self.heightSpin)

        self.label13 = QLabel(self.generalTab)
        self.label13.setObjectName(u"label13")

        self.generalForm.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label13)

        self.bubbleFontSpin = QSpinBox(self.generalTab)
        self.bubbleFontSpin.setObjectName(u"bubbleFontSpin")
        self.bubbleFontSpin.setMinimum(8)
        self.bubbleFontSpin.setMaximum(200)

        self.generalForm.setWidget(3, QFormLayout.ItemRole.FieldRole, self.bubbleFontSpin)

        self.autoSaveCheck = QCheckBox(self.generalTab)
        self.autoSaveCheck.setObjectName(u"autoSaveCheck")
        self.autoSaveCheck.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.generalForm.setWidget(4, QFormLayout.ItemRole.FieldRole, self.autoSaveCheck)

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

        self.tabs.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(SettingsWindow)
    # setupUi

    def retranslateUi(self, SettingsWindow):
        SettingsWindow.setWindowTitle(QCoreApplication.translate("SettingsWindow", u"4cut Studio - \uc124\uc815", None))
        self.lmGroup.setTitle(QCoreApplication.translate("SettingsWindow", u"LM Studio \u00b7 \uc774\uc57c\uae30/\ub300\uc0ac \uc0dd\uc131", None))
        self.lmHostLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc11c\ubc84 \uc8fc\uc18c", None))
        self.lmPortLabel.setText(QCoreApplication.translate("SettingsWindow", u"\ud3ec\ud2b8", None))
        self.lmApiLabel.setText(QCoreApplication.translate("SettingsWindow", u"API \uacbd\ub85c", None))
        self.lmModelLabel.setText(QCoreApplication.translate("SettingsWindow", u"\ubaa8\ub378", None))
        self.lmTestButton.setText(QCoreApplication.translate("SettingsWindow", u"\uc5f0\uacb0 \ud14c\uc2a4\ud2b8", None))
        self.lmStatusLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc0c1\ud0dc: \ud14c\uc2a4\ud2b8 \uc804", None))
        self.comfyGroup.setTitle(QCoreApplication.translate("SettingsWindow", u"ComfyUI \u00b7 \uc774\ubbf8\uc9c0 \uc0dd\uc131", None))
        self.comfyHostLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc11c\ubc84 \uc8fc\uc18c", None))
        self.comfyPortLabel.setText(QCoreApplication.translate("SettingsWindow", u"\ud3ec\ud2b8", None))
        self.comfyWorkflowLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uae30\ubcf8 Workflow", None))
        self.browseWorkflowButton.setText(QCoreApplication.translate("SettingsWindow", u"\ucc3e\uc544\ubcf4\uae30", None))
        self.comfyTestButton.setText(QCoreApplication.translate("SettingsWindow", u"\uc5f0\uacb0 \ud14c\uc2a4\ud2b8", None))
        self.comfyStatusLabel.setText(QCoreApplication.translate("SettingsWindow", u"\uc0c1\ud0dc: \ud14c\uc2a4\ud2b8 \uc804", None))
        self.tabs.setTabText(self.tabs.indexOf(self.aiServerTab), QCoreApplication.translate("SettingsWindow", u"AI \uc11c\ubc84", None))
        self.imageModelListLabel.setText(QCoreApplication.translate("SettingsWindow", u"\ub4f1\ub85d\ub41c \uc774\ubbf8\uc9c0 \ubaa8\ub378", None))
        self.addImageModelButton.setText(QCoreApplication.translate("SettingsWindow", u"+ \ucd94\uac00", None))
        self.removeImageModelButton.setText(QCoreApplication.translate("SettingsWindow", u"\uc0ad\uc81c", None))
        self.label.setText(QCoreApplication.translate("SettingsWindow", u"\ubaa8\ub378 \uc774\ub984", None))
        self.label1.setText(QCoreApplication.translate("SettingsWindow", u"\ubaa8\ub378 \ud30c\uc77c", None))
        self.browseImageModelButton.setText(QCoreApplication.translate("SettingsWindow", u"\ucc3e\uc544\ubcf4\uae30", None))
        self.label2.setText(QCoreApplication.translate("SettingsWindow", u"Workflow", None))
        self.browseImageModelWorkflowButton.setText(QCoreApplication.translate("SettingsWindow", u"\ucc3e\uc544\ubcf4\uae30", None))
        self.label3.setText(QCoreApplication.translate("SettingsWindow", u"\ub108\ube44", None))
        self.label4.setText(QCoreApplication.translate("SettingsWindow", u"\ub192\uc774", None))
        self.label5.setText(QCoreApplication.translate("SettingsWindow", u"Steps", None))
        self.label6.setText(QCoreApplication.translate("SettingsWindow", u"CFG", None))
        self.label7.setText(QCoreApplication.translate("SettingsWindow", u"Sampler", None))
        self.label8.setText(QCoreApplication.translate("SettingsWindow", u"Scheduler", None))
        self.label9.setText(QCoreApplication.translate("SettingsWindow", u"Negative Prompt", None))
        self.saveImageModelButton.setText(QCoreApplication.translate("SettingsWindow", u"\ubaa8\ub378 \uc815\ubcf4 \uc800\uc7a5", None))
        self.tabs.setTabText(self.tabs.indexOf(self.imageModelTab), QCoreApplication.translate("SettingsWindow", u"\uc774\ubbf8\uc9c0 \ubaa8\ub378", None))
        self.label10.setText(QCoreApplication.translate("SettingsWindow", u"\ud504\ub85c\uc81d\ud2b8 \uc800\uc7a5 \uc704\uce58", None))
        self.label11.setText(QCoreApplication.translate("SettingsWindow", u"\uc774\ubbf8\uc9c0 \ub108\ube44", None))
        self.label12.setText(QCoreApplication.translate("SettingsWindow", u"\uc774\ubbf8\uc9c0 \ub192\uc774", None))
        self.label13.setText(QCoreApplication.translate("SettingsWindow", u"\ub9d0\ud48d\uc120 \uae00\uc790 \ud06c\uae30", None))
        self.autoSaveCheck.setText(QCoreApplication.translate("SettingsWindow", u"\uacb0\uacfc \uc790\ub3d9 \uc800\uc7a5", None))
        self.tabs.setTabText(self.tabs.indexOf(self.generalTab), QCoreApplication.translate("SettingsWindow", u"\uc77c\ubc18", None))
        self.cancelButton.setText(QCoreApplication.translate("SettingsWindow", u"\ucde8\uc18c", None))
        self.applyButton.setText(QCoreApplication.translate("SettingsWindow", u"\uc801\uc6a9", None))
    # retranslateUi

