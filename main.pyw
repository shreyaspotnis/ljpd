import ConfigParser
import sys
import string
from PyQt4 import QtGui, QtCore
import matplotlib
from datetime import datetime

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import labjacksingle
import logger

# hack for TV show
from numpy.random import random

class MainWindow(QtGui.QMainWindow):
    def __init__(self, config, internal_config):
        super(MainWindow, self).__init__()

        self.config = config
        self.internal_config = internal_config

        self.initUI()
    def initUI(self):
 
        # set the central widget
        self.cw = CentralWidget(self.config, self.internal_config)
        self.setWindowTitle('PD-LabJack')
        self.setCentralWidget(self.cw)

        # set the font 
        self.font_name = self.config.get('gui-settings','FONT_NAME')
        self.font_point_size = self.config.getint('gui-settings','FONT_POINT_SIZE')
        self.font = QtGui.QFont(self.font_name, self.font_point_size)
        self.cw.setFont(self.font)


        # add actions
        exitAction = QtGui.QAction('E&xit', self)
        exitAction.setShortcut('Ctrl+Q')
        #exitAction.triggered.connect(QtCore.QCoreApplication.instance().quit)
        #exitAction.triggered.connect(QtGui.qApp.quit)

        self.takeSnapshotAction = QtGui.QAction('&Take', self)
        self.takeSnapshotAction.triggered.connect(self.cw.takeSnapshot)
        
        self.loadSnapshotAction = QtGui.QAction('&Load', self)
        self.loadSnapshotAction.triggered.connect(self.cw.loadSnapshot)

        self.copyPastaAction = QtGui.QAction('Copypasta', self)
        self.copyPastaAction.triggered.connect(self.cw.copyPasta)
        self.copyPastaAction.setShortcut('Ctrl+C')

        self.showPlotAction = QtGui.QAction('&Show', self)
        self.showPlotAction.triggered.connect(self.cw.showPlot)
        
        self.editConfigAction = QtGui.QAction('&Reload config.ini', self)
        self.editConfigAction.triggered.connect(self.reloadCentralWidget)

        menubar = self.menuBar()
        #fileMenu = menubar.addMenu('&File')
        #fileMenu.addAction(exitAction)

        snapshotMenu = menubar.addMenu('&Snapshot')
        snapshotMenu.addAction(self.takeSnapshotAction)
        snapshotMenu.addAction(self.loadSnapshotAction)
        snapshotMenu.addAction(self.copyPastaAction)

        plotMenu = menubar.addMenu('&Plot')
        plotMenu.addAction(self.showPlotAction)

        editMenu = menubar.addMenu('&Settings')
        editMenu.addAction(self.editConfigAction)


        self.show()
    def reloadCentralWidget(self):
        # setup config parser
        self.config = ConfigParser.SafeConfigParser(allow_no_value=True)
        self.internal_config = ConfigParser.SafeConfigParser(allow_no_value=True)
        self.config.read("config.ini")
        self.internal_config.read("internal_config.ini")

        # close labjack
        self.cw.ljs.closeLJ()
    
        # set the central widget
        self.cw = CentralWidget(self.config, self.internal_config)
        self.setCentralWidget(self.cw)

        self.takeSnapshotAction.triggered.connect(self.cw.takeSnapshot)
        self.loadSnapshotAction.triggered.connect(self.cw.loadSnapshot)
        self.showPlotAction.triggered.connect(self.cw.showPlot)
        self.editConfigAction.triggered.connect(self.reloadCentralWidget)

        
        
class CentralWidget(QtGui.QWidget):

    # This signal is emmited whenever we use logger to log new data read from
    # labjack
    dataUpdated= QtCore.pyqtSignal()

    def __init__(self, config, internal_config):
        super(CentralWidget, self).__init__()
        
        # get a copy of the config object
        self.config = config
        self.internal_config = internal_config
        # Start labjack
        self.ljs = labjacksingle.LabJackSingle()
        self.all_channels = self.ljs.getAllChannels()

        # load settings from config.ini
        self.getConfig()

        # configure labjack to read all channels, even if we are not displaying
        # all of them. This is because logging all channels is beneficial even
        # if we do not want to monitor them.
        self.ljs.configure()

    
        # start the logger
        self.log = logger.Logger(self.config, self.channel_labels) 
        self.initUI()

    def getConfig(self):
         # get labels for all the channels
        self.channel_labels = [] 
        for key in self.all_channels:
            self.channel_labels.append(self.config.get('channel_labels', key))

        # find out what channels are being used currently
        ch_used_string =  self.config.items('channels_used')
        self.channels_used = []
        for ch in ch_used_string:
            self.channels_used.append(int(ch[0][3:]))

        # get all the big displays
        self.big_displays = self.config.items('big_displays')

        # get read speed in Hz, convert it into a value in milliseconds
        self.timer_value = int(1000/float(self.config.get('settings','READ_RATE')))

    def initUI(self):
        # set the font 
        self.font_name = self.config.get('gui-settings','FONT_NAME')
        self.font_point_size = self.config.getint('gui-settings','FONT_POINT_SIZE')
        self.font_big_point_size_numbers = self.config.getint('gui-settings',
                                    'BIG_FONT_POINT_SIZE_NUMBERS')
        self.font_big_point_size_labels = self.config.getint('gui-settings',
                                    'BIG_FONT_POINT_SIZE_LABELS')
        self.font = QtGui.QFont(self.font_name, self.font_point_size)
        self.font_big_numbers = QtGui.QFont(self.font_name,
                                    self.font_big_point_size_numbers)
        self.font_big_labels = QtGui.QFont(self.font_name,
                                    self.font_big_point_size_labels)
        self.setFont(self.font)


        self.grid = QtGui.QGridLayout()
        self.createVoltageBoxes()
        #self.createPlots()

        self.setLayout(self.grid)

        # start the timer
        self.timer = QtCore.QBasicTimer()
        self.timer.start(self.timer_value, self)

    def createVoltageBoxes(self):
        nchannels = len(self.channels_used)
        
        # create boxes to display PD readings
        self.displayboxes = []
        self.snapshotboxes = []
        self.labels = []

        self.biglabels = []
        self.bigboxes = []
        self.bigsnaps = []

        for i, ch in zip(range(nchannels), self.channels_used):
            # create boxes to display numbers
            dp = QtGui.QLineEdit(self)
            dp_snap = QtGui.QLineEdit(self)

            dp.setReadOnly(True)
            dp_snap.setReadOnly(True)
            dp.setText('{0:.2f}'.format(0.0))
            dp_snap.setText('{0:.2f}'.format(0.0))

            # create labels
            lbl = QtGui.QLabel(self.channel_labels[ch], self)
            lbl.setToolTip('AIN'+str(ch))
            self.displayboxes.append(dp)
            self.snapshotboxes.append(dp_snap)
            self.labels.append(lbl)
            self.grid.addWidget(lbl, i+1, 0, 1, 1)
            self.grid.addWidget(dp, i+1, 1, 1, 1)
            self.grid.addWidget(dp_snap, i+1, 2, 1, 1)
   
        # create the big display boxes
        label_no = 0
        self.big_formulae = []
        for label, formula in self.big_displays:
            dp = QtGui.QLineEdit(self)
            sp = QtGui.QLineEdit(self)
            dp.setReadOnly(True)
            sp.setReadOnly(True)
            dp.setText('{0:.2f}'.format(0.0))
            sp.setText('{0:.2f}'.format(0.0))
            
            lbl = QtGui.QLabel(label, self)

            dp.setFont(self.font_big_numbers)
            sp.setFont(self.font_big_labels)
            lbl.setFont(self.font_big_labels)

            self.bigboxes.append(dp)
            self.bigsnaps.append(sp)
            self.biglabels.append(lbl)

            self.grid.addWidget(lbl, label_no*3, 4, 1, 3)
            self.grid.addWidget(dp, 1+label_no*3, 4, 2, 2)
            self.grid.addWidget(sp, 2+label_no*3, 6, 1, 1)
#            self.grid.setColumnStretch(3, 1)

            self.big_formulae.append(formula)
            label_no+=1

        # get which snapshot is being used
        snap_list_name = self.internal_config.get('snapshot', 'current')

        # get data for the snapshot
        snap_stuff = self.log.loadsnapshot()
        for sdate, stime, sdata, scomment in zip(snap_stuff[0], snap_stuff[1],
            snap_stuff[2], snap_stuff[3]):
            if snap_list_name == sdate+' '+stime:
                self.updateSnapshot(sdate, stime, sdata, scomment)
                self.snap_data = sdata

        self.grid.addWidget(QtGui.QLabel('Recordings', self), 0, 1, 1, 1)
        self.grid.addWidget(QtGui.QLabel('Snapshot', self), 0, 2, 1, 1)

    def showPlot(self):
        pw = PlotWindow(self, self.log, self.dataUpdated)

    def timerEvent(self, e):
        voltages = self.ljs.read()
        # Hack for TV show, because experiment doesnt work
        # voltages = [390.98, 1406.21, 1404.11, -7.73, 819.51, 914.31, 347.43, 226.29, 259.25, 898.55, 932.97, 331.65, 358.32, 1402.64, 2.05, 1985.40]
        # voltages += 70*random(len(voltages))

        self.log.log(voltages)
        self.dataUpdated.emit()
      
        # self.plotGraphs()
        for dp, ch in zip(self.displayboxes, self.channels_used):
            dp.setText('{0:.0f}'.format(voltages[ch]))

        # create a dictionary for evaluating big_formulae
        d = dict(zip(self.all_channels, voltages))
        for dp, formula in zip(self.bigboxes, self.big_formulae):
            dp.setText('{0:.0f}'.format(eval(formula, d))) 

    def copyPasta(self, e):
        infoString = ""        
        for label, dp, sp in zip(self.labels, self.displayboxes, self.snapshotboxes):
            infoString += label.text() +"\t" + dp.text() +"\t" + sp.text() +"\n"
        for label, dp, sp in zip(self.biglabels, self.bigboxes, self.bigsnaps):
            infoString += label.text() +"\t" + dp.text() +"\t" + sp.text() +"\n"

        clipboard = QtGui.QApplication.clipboard()
        clipboard.setText(infoString)
        print infoString

    def takeSnapshot(self, e):
        
        # get a comment from the user
        comment, ok = QtGui.QInputDialog.getText(self, 'Input Dialog', 
                    'Comment for the snapshot:')
        if ok:
            # stop regular logging
            self.timer.stop()

            start_time = datetime.now()
            time_average = self.config.getint('settings', 'LOG_SNAPSHOT_AVERAGE')
            done = False
            n_averages = 1
            voltages = self.ljs.read(averages = 1)
            while not done:
                v_curr = self.ljs.read(averages = 1)
                for i in range(len(v_curr)):
                    voltages[i]+=v_curr[i]
                
                n_averages += 1
                delta_time = datetime.now()-start_time
                n_ms = delta_time.seconds*1000+delta_time.microseconds/1000
                if n_ms >= time_average:
                    done = True
            for i in range(len(voltages)):
                voltages[i] = voltages[i]/n_averages
            self.log.savesnapshot(voltages, str(comment))
            # resumer regular logging
            self.timer.start(self.timer_value, self)


    def loadSnapshot(self, e):
        # get saved snapshot data
        snap_stuff = self.log.loadsnapshot()
        sd = SnapDialog(self, snap_stuff, self.updateSnapshot)

    def updateSnapshot(self, snap_date, snap_time, snap_data, snap_comment):
        for dp, i in zip(self.snapshotboxes, self.channels_used):
            value = snap_data[i]
            dp.setText('{0:.2f}'.format(value))
        d = dict(zip(self.all_channels, snap_data))
        for dp, formula in zip(self.bigsnaps, self.big_formulae):
            dp.setText('{0:.0f}'.format(eval(formula, d)))
        """
        # create a dictionary for evaluation
        d = dict(zip(self.all_channels, snap_data))
        for dp, formula in zip(self.bigsnaps, self.big_formulae):
            dp.setText('{0:.0f}'.format(eval(formula, dict(zip(self.all_channels,
                snap_data)))))
        """
        # update internal_config, and save the data
        fp = open('internal_config.ini', 'w')
        self.internal_config.set('snapshot', 'current', str(snap_date+
        ' '+snap_time))
        self.internal_config.write(fp)
        fp.close()

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

# create a dialog box to browse through snap data
class SnapDialog(QtGui.QDialog):

    # create a signal to notify that the process of selection is
    # done
    snapSelected = QtCore.pyqtSignal(str, str, list, str)

    def __init__(self, parent, snap_stuff, updateSnapshot):
        super(SnapDialog, self).__init__(parent)

        self.snap_stuff = snap_stuff
        self.snapSelected.connect(updateSnapshot)

        self.snap_list = QtGui.QListWidget(self)
        self.snap_items = []
        #self.qsnap_items = []
        for sdate, stime in zip(snap_stuff[0], snap_stuff[1]): 
            snap_id = sdate+' '+stime
            self.snap_items.append(snap_id)
            #self.qsnap_items.append(QtGui.QListWidgetItem(snap_id,
            self.snap_list.addItem(snap_id)
#            listitem = (QtGui.QListWidgetItem(snap_id,
#            self.snap_list))

        self.snap_list.currentItemChanged.connect(self.itemChanged)

        # insert label
        lbl_comment = QtGui.QLabel('Comment:', self)
        lbl_snapshot = QtGui.QLabel('Snapshot:', self)
        
        # comment box
        self.comment_box = QtGui.QTextEdit(self)
        self.comment_box.setReadOnly(True)

        # buttons
        update_button = QtGui.QPushButton("&Update", self)
        close_button = QtGui.QPushButton("&Close", self)

        # connect the cancel button to closing the dialog
        close_button.clicked.connect(self.close)

        # connect the ok button to accepting a value
        update_button.clicked.connect(self.acceptSnapshot)
        # grid
        grid = QtGui.QGridLayout()

        grid.addWidget(lbl_snapshot, 0, 0)
        grid.addWidget(self.snap_list, 1, 0, 10, 10)
        grid.addWidget(lbl_comment, 0, 11)
        grid.addWidget(self.comment_box, 1, 11, 10, 10)
        grid.addWidget(update_button, 12, 0)
        grid.addWidget(close_button, 12, 5)


        #self.resize(400, 300)
        self.resize(self.sizeHint())
        self.setWindowTitle("Browse Snapshots")
        self.setLayout(grid)

        self.show()

    def acceptSnapshot(self, e):
        # get the current selected item
        curr_item = self.snap_list.currentItem().text()

        # get the index to the current item
        curr_index = self.snap_items.index(curr_item)

        # emit a signal saying that we are done
        sdate = self.snap_stuff[0][curr_index]
        stime = self.snap_stuff[1][curr_index]
        sdata = self.snap_stuff[2][curr_index]
        scomment = self.snap_stuff[3][curr_index]

        self.snapSelected.emit(sdate, stime, sdata, scomment)

    def itemChanged(self, clicked_item, prev_item):
        # find out what item was clicked
        click_id = clicked_item.text()
        index = self.snap_items.index(click_id)

        # update the comment box with the new comment
        self.comment_box.setText(self.snap_stuff[3][index])



def main():
    # setup config parser
    config = ConfigParser.SafeConfigParser(allow_no_value=True)
    internal_config = ConfigParser.SafeConfigParser(allow_no_value=True)
    config.read("config.ini")
    internal_config.read("internal_config.ini")

    app = QtGui.QApplication(sys.argv)
   
    w = MainWindow(config, internal_config)

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
