# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'assets/qt/NetworkSettingsDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.11
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_NetworkSettingsDialog(object):
    def setupUi(self, NetworkSettingsDialog):
        NetworkSettingsDialog.setObjectName("NetworkSettingsDialog")
        NetworkSettingsDialog.resize(600, 355)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(NetworkSettingsDialog.sizePolicy().hasHeightForWidth())
        NetworkSettingsDialog.setSizePolicy(sizePolicy)
        NetworkSettingsDialog.setMinimumSize(QtCore.QSize(600, 0))
        NetworkSettingsDialog.setMaximumSize(QtCore.QSize(16777215, 355))
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(NetworkSettingsDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.networkBox = QtWidgets.QGroupBox(NetworkSettingsDialog)
        self.networkBox.setObjectName("networkBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.networkBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.label_3 = QtWidgets.QLabel(self.networkBox)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_10.addWidget(self.label_3)
        self.serverModeComboBox = QtWidgets.QComboBox(self.networkBox)
        self.serverModeComboBox.setObjectName("serverModeComboBox")
        self.serverModeComboBox.addItem("")
        self.serverModeComboBox.addItem("")
        self.horizontalLayout_10.addWidget(self.serverModeComboBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_10.addItem(spacerItem)
        self.asdLabel = QtWidgets.QLabel(self.networkBox)
        self.asdLabel.setObjectName("asdLabel")
        self.horizontalLayout_10.addWidget(self.asdLabel)
        self.verticalLayout.addLayout(self.horizontalLayout_10)
        self.label_6 = QtWidgets.QLabel(self.networkBox)
        self.label_6.setObjectName("label_6")
        self.verticalLayout.addWidget(self.label_6)
        self.serverIpLineEdit = QtWidgets.QLineEdit(self.networkBox)
        self.serverIpLineEdit.setObjectName("serverIpLineEdit")
        self.verticalLayout.addWidget(self.serverIpLineEdit)
        self.label_7 = QtWidgets.QLabel(self.networkBox)
        self.label_7.setObjectName("label_7")
        self.verticalLayout.addWidget(self.label_7)
        self.serverPortLineEdit = QtWidgets.QLineEdit(self.networkBox)
        self.serverPortLineEdit.setObjectName("serverPortLineEdit")
        self.verticalLayout.addWidget(self.serverPortLineEdit)
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_11.addItem(spacerItem1)
        self.deleteConfigButton = QtWidgets.QPushButton(self.networkBox)
        self.deleteConfigButton.setObjectName("deleteConfigButton")
        self.horizontalLayout_11.addWidget(self.deleteConfigButton)
        self.verticalLayout.addLayout(self.horizontalLayout_11)
        self.horizontalLayout_3.addWidget(self.networkBox)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.groupBox = QtWidgets.QGroupBox(NetworkSettingsDialog)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.defaultImageLineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.defaultImageLineEdit.setEnabled(True)
        self.defaultImageLineEdit.setReadOnly(True)
        self.defaultImageLineEdit.setPlaceholderText("")
        self.defaultImageLineEdit.setObjectName("defaultImageLineEdit")
        self.gridLayout.addWidget(self.defaultImageLineEdit, 1, 1, 1, 1)
        self.findButton = QtWidgets.QPushButton(self.groupBox)
        self.findButton.setObjectName("findButton")
        self.gridLayout.addWidget(self.findButton, 1, 2, 1, 1)
        self.imagesDirectoryLineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.imagesDirectoryLineEdit.setObjectName("imagesDirectoryLineEdit")
        self.gridLayout.addWidget(self.imagesDirectoryLineEdit, 0, 1, 1, 2)
        self.verticalLayout_4.addLayout(self.gridLayout)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem2)
        self.cancelButton = QtWidgets.QPushButton(NetworkSettingsDialog)
        self.cancelButton.setObjectName("cancelButton")
        self.horizontalLayout_12.addWidget(self.cancelButton)
        self.saveButton = QtWidgets.QPushButton(NetworkSettingsDialog)
        self.saveButton.setObjectName("saveButton")
        self.horizontalLayout_12.addWidget(self.saveButton)
        self.verticalLayout_2.addLayout(self.horizontalLayout_12)

        self.retranslateUi(NetworkSettingsDialog)
        QtCore.QMetaObject.connectSlotsByName(NetworkSettingsDialog)

    def retranslateUi(self, NetworkSettingsDialog):
        _translate = QtCore.QCoreApplication.translate
        NetworkSettingsDialog.setWindowTitle(_translate("NetworkSettingsDialog", "Pinolo - Network settings"))
        self.networkBox.setTitle(_translate("NetworkSettingsDialog", "Connection settings"))
        self.label_3.setText(_translate("NetworkSettingsDialog", "Server mode"))
        self.serverModeComboBox.setItemText(0, _translate("NetworkSettingsDialog", "Local"))
        self.serverModeComboBox.setItemText(1, _translate("NetworkSettingsDialog", "Remote"))
        self.asdLabel.setText(_translate("NetworkSettingsDialog", "asdLabel"))
        self.label_6.setText(_translate("NetworkSettingsDialog", "IP Address:"))
        self.label_7.setText(_translate("NetworkSettingsDialog", "Port:"))
        self.deleteConfigButton.setText(_translate("NetworkSettingsDialog", "Delete this IP"))
        self.groupBox.setTitle(_translate("NetworkSettingsDialog", "Disk image settings"))
        self.label.setText(_translate("NetworkSettingsDialog", "Images directory"))
        self.label_2.setText(_translate("NetworkSettingsDialog", "Default image"))
        self.findButton.setText(_translate("NetworkSettingsDialog", "Select default image"))
        self.imagesDirectoryLineEdit.setPlaceholderText(_translate("NetworkSettingsDialog", "/path/to/folder/of/images/"))
        self.cancelButton.setText(_translate("NetworkSettingsDialog", "Cancel"))
        self.saveButton.setText(_translate("NetworkSettingsDialog", "Save"))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    NetworkSettingsDialog = QtWidgets.QDialog()
    ui = Ui_NetworkSettingsDialog()
    ui.setupUi(NetworkSettingsDialog)
    NetworkSettingsDialog.show()
    sys.exit(app.exec_())
