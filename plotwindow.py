from PyQt4 import QtGui, QtCore
import matplotlib

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class PlotWindow(QtGui.QDialog):
    def __init__(self, parent, log, updateSignal):
        super(PlotWindow, self).__init__(parent)
        self.updateSignal = updateSignal
        self.log = log
        self.initUI()
        updateSignal.connect(self.updatePlot)

    def initUI(self):
        self.plot_frame = QtGui.QWidget()
        
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

        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        self.fig = Figure((6.0, 5.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.plot_frame)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        self.axes = self.fig.add_subplot(111)
        
        # Bind the 'pick' event for clicking on one of the bars
        #
        #self.canvas.mpl_connect('pick_event', self.on_pick)
        
        # Create the navigation toolbar, tied to the canvas
        #self.mpl_toolbar = NavigationToolbar(self.canvas, self.plot_frame)

        # initialize the plotting region
        #self.axes.clear()
    
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


        # plot something initially
        self.line = self.axes.plot(self.log.logdict['time'], 
            self.log.logdict['AIN0'])[0]

        # get the background for the plot
        self.background = self.fig.canvas.copy_from_bbox(self.axes.bbox)

        # draw the canvas once
        self.canvas.draw()
        #self.fig.show()
        
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
        self.axes.clear()
        if self.x_plotting_string == 'time':
            self.axes.axvline(x=ind)
            self.axes.plot(x_array, y_array, linewidth=2.0)
        else:
            self.axes.plot(x_array, y_array, 'o')

        self.canvas.draw()

    def closeEvent(self, event):
       event.accept()
       self.updateSignal.disconnect(self.updatePlot)