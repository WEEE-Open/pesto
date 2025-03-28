# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'assets/qt/SmartDataDialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.11
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SmartDataDialog(object):
    def setupUi(self, SmartDataDialog):
        SmartDataDialog.setObjectName("SmartDataDialog")
        SmartDataDialog.resize(702, 499)
        self.verticalLayout = QtWidgets.QVBoxLayout(SmartDataDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.searchLineEdit = QtWidgets.QLineEdit(SmartDataDialog)
        self.searchLineEdit.setText("")
        self.searchLineEdit.setObjectName("searchLineEdit")
        self.verticalLayout.addWidget(self.searchLineEdit)
        self.treeWidget = QtWidgets.QTreeWidget(SmartDataDialog)
        self.treeWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.treeWidget.setIconSize(QtCore.QSize(5, 5))
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.headerItem().setText(0, "Key")
        self.verticalLayout.addWidget(self.treeWidget)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(SmartDataDialog)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.statusLineEdit = QtWidgets.QLineEdit(SmartDataDialog)
        self.statusLineEdit.setEnabled(False)
        self.statusLineEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.statusLineEdit.setObjectName("statusLineEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.statusLineEdit)
        self.updateAtLabel = QtWidgets.QLabel(SmartDataDialog)
        self.updateAtLabel.setObjectName("updateAtLabel")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.updateAtLabel)
        self.label_2 = QtWidgets.QLabel(SmartDataDialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.verticalLayout.addLayout(self.formLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.exportButton = QtWidgets.QPushButton(SmartDataDialog)
        self.exportButton.setObjectName("exportButton")
        self.horizontalLayout.addWidget(self.exportButton)
        self.closeButton = QtWidgets.QPushButton(SmartDataDialog)
        self.closeButton.setObjectName("closeButton")
        self.horizontalLayout.addWidget(self.closeButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.actionCollapse_All = QtWidgets.QAction(SmartDataDialog)
        self.actionCollapse_All.setObjectName("actionCollapse_All")
        self.actionExpand_All = QtWidgets.QAction(SmartDataDialog)
        self.actionExpand_All.setObjectName("actionExpand_All")

        self.retranslateUi(SmartDataDialog)
        QtCore.QMetaObject.connectSlotsByName(SmartDataDialog)

    def retranslateUi(self, SmartDataDialog):
        _translate = QtCore.QCoreApplication.translate
        SmartDataDialog.setWindowTitle(_translate("SmartDataDialog", "SMART Data - ?"))
        self.searchLineEdit.setPlaceholderText(_translate("SmartDataDialog", "Search key ..."))
        self.treeWidget.headerItem().setText(1, _translate("SmartDataDialog", "Value"))
        self.label.setText(_translate("SmartDataDialog", "Drive status"))
        self.updateAtLabel.setText(_translate("SmartDataDialog", "1970-01-01"))
        self.label_2.setText(_translate("SmartDataDialog", "Updated at"))
        self.exportButton.setText(_translate("SmartDataDialog", "Export Data"))
        self.closeButton.setText(_translate("SmartDataDialog", "Close"))
        self.actionCollapse_All.setText(_translate("SmartDataDialog", "Collapse All"))
        self.actionExpand_All.setText(_translate("SmartDataDialog", "Expand All"))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    SmartDataDialog = QtWidgets.QWidget()
    ui = Ui_SmartDataDialog()
    ui.setupUi(SmartDataDialog)
    SmartDataDialog.show()
    sys.exit(app.exec_())
