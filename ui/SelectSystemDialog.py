# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'assets/qt/SelectSystemDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.11
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SelectSystemDialog(object):
    def setupUi(self, SelectSystemDialog):
        SelectSystemDialog.setObjectName("SelectSystemDialog")
        SelectSystemDialog.resize(269, 262)
        self.verticalLayout = QtWidgets.QVBoxLayout(SelectSystemDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.dialogLabel = QtWidgets.QLabel(SelectSystemDialog)
        self.dialogLabel.setObjectName("dialogLabel")
        self.verticalLayout.addWidget(self.dialogLabel)
        self.isoList = QtWidgets.QListWidget(SelectSystemDialog)
        self.isoList.setObjectName("isoList")
        self.verticalLayout.addWidget(self.isoList)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.cancelButton = QtWidgets.QPushButton(SelectSystemDialog)
        self.cancelButton.setObjectName("cancelButton")
        self.horizontalLayout.addWidget(self.cancelButton)
        self.selectButton = QtWidgets.QPushButton(SelectSystemDialog)
        self.selectButton.setObjectName("selectButton")
        self.horizontalLayout.addWidget(self.selectButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(SelectSystemDialog)
        QtCore.QMetaObject.connectSlotsByName(SelectSystemDialog)

    def retranslateUi(self, SelectSystemDialog):
        _translate = QtCore.QCoreApplication.translate
        SelectSystemDialog.setWindowTitle(_translate("SelectSystemDialog", "Select default image"))
        self.dialogLabel.setText(_translate("SelectSystemDialog", "Select one of the following images"))
        self.cancelButton.setText(_translate("SelectSystemDialog", "Cancel"))
        self.selectButton.setText(_translate("SelectSystemDialog", "Select"))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    SelectSystemDialog = QtWidgets.QDialog()
    ui = Ui_SelectSystemDialog()
    ui.setupUi(SelectSystemDialog)
    SelectSystemDialog.show()
    sys.exit(app.exec_())
