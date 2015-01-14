from PyQt4 import QtGui, QtCore
import pyqtgraph as pg


class PlotWindow(QtGui.QDialog):
    def __init__(self, parent, log, updateSignal):
        super(PlotWindow, self).__init__(parent)
        self.updateSignal = updateSignal
        self.log = log
        self.initUI()
        updateSignal.connect(self.updatePlot)

    def initUI(self):
        # create a textbox and a label for the plotting formula
        xlbl = QtGui.QLabel('x-axis', self)
        ylbl = QtGui.QLabel('y-axis', self)

        self.xtxt = QtGui.QLineEdit(self)
        self.ytxt = QtGui.QLineEdit(self)

        self.xtxt.setText('time')
        self.ytxt.setText('AIN0')

        self.x_plotting_string = 'time'
        self.y_plotting_string = 'AIN0'

        update_button = QtGui.QPushButton('&Update', self)
        help_button = QtGui.QPushButton('&Help', self)

        update_button.clicked.connect(self.updateFormula)
        help_button.clicked.connect(self.showHelp)

        self.plot_frame = pg.PlotWidget()
        self.p1 = self.plot_frame.plot()
        self.p1.setPen(0)

        self.grid = QtGui.QGridLayout()
        self.grid.addWidget(xlbl, 0, 0)
        self.grid.addWidget(ylbl, 1, 0)
        self.grid.addWidget(self.xtxt, 0, 1)
        self.grid.addWidget(self.ytxt, 1, 1)
        self.grid.addWidget(help_button, 0, 2)
        self.grid.addWidget(update_button, 1, 2)

        self.grid.addWidget(self.plot_frame, 2, 0, 3, 3)

        self.setLayout(self.grid)

        self.resize(610, 610)
        self.setWindowTitle('Plots')

        self.show() 

    def updateFormula(self, e):
        self.x_plotting_string

        # get the text from the textboxes
        temp_x = str(self.xtxt.text())
        temp_y = str(self.ytxt.text())

        # try to evaluate this
        try:
            eval(temp_x, self.log.logdict)
            eval(temp_y, self.log.logdict)
        except:
            QtGui.QMessageBox.critical(self, 'Parsing error:'+str(sys.exc_info()[0]),
                str(sys.exc_info()[1]), QtGui.QMessageBox.Ok)
        else:
            self.x_plotting_string = temp_x
            self.y_plotting_string = temp_y

    def showHelp(self, e):
        str = """Enter what you want the x-axis and y-axis on the plot to be. For
example, if you want to plot AIN0 as a function of time, enter 'time' as
the x-axis and 'AIN0' as the y-axis. To plot AIN3 as function of AIN2,
enter 'AIN2' as x-axis and 'AIN3' as the y-axis. You can even enter
complicated formulae like AIN3+2.0*AIN12, etc."""

        help_message = QtGui.QMessageBox()
        help_message.setText(str)
        help_message.exec_()

    def updatePlot(self):

        y_array = eval(self.y_plotting_string, self.log.logdict)
        x_array = eval(self.x_plotting_string, self.log.logdict)
        
        ind = self.log.n_log_curr

        self.p1.setData(x=x_array, y=y_array)

    def closeEvent(self, event):
       event.accept()
       self.updateSignal.disconnect(self.updatePlot)