"""Implements a class to conveniently get single measurements from LabjackU3."""

import u3, LabJackPython
from time import sleep
from datetime import datetime
import time
import struct
import os
import cStringIO
import threading
import Queue
import ctypes, copy, sys

# define MODBUS registers

FIO_ANALOG = 50590
EIO_ANALOG = 50591

class LabJackSingle(object):

    def __init__(self, config):
         # create a list of all channels
        self.all_channels = ['AIN0', 'AIN1', 'AIN2', 'AIN3', 'AIN4',
                         'AIN5', 'AIN6', 'AIN7', 'AIN8', 'AIN9',
                         'AIN10', 'AIN11', 'AIN12', 'AIN13', 'AIN14','AIN15']


        self.config = config

        # load settings from config.ini
        self.getConfig()

        #Get a start time for timestamping streams
        self.start = 0.0

    def getConfig(self):
        #get stream settings from config.ini
        self.streamChannels = map(int, self.config.get('stream_settings','streamChannels').split(','))
        self.triggerChannel = self.config.getint('stream_settings','triggerChannel')
        self.sampleFrequency = self.config.getint('stream_settings','sampleFrequency')
        self.resolution = self.config.getint('stream_settings','resolution')
        self.numChannels = self.config.getint('stream_settings','numChannels')
        self.streamFolder = self.config.get('stream_settings', 'streamFolder')

        #Stringstream to hold data while streaming
        self.streamHold = cStringIO.StringIO()

    def configure(self, channels = None):
        """Opens labjack and configures to read analog signals.

        channels - List of channel addresses to be read.
        e.g in channels = [0, 2, 15], then read AIN0, AIN2, AIN15
        """
        # initialize a labjack u3 device
        print "Getting a handle for LabJack"
        try:
            self.d = u3.U3()
        except LabJackPython.NullHandleException:
            print "Could not open device. Please check that the device you are trying to open is connected"
            sys.exit(1)

        # get the labjack configuration
        self.ljconfig = self.d.configU3()

        if(self.ljconfig['DeviceName'] != 'U3-HV'):
            print "Sorry, your device %s is not supported. Only U3-HV is supported" % self.ljconfig['DeviceName']
            sys.exit(1)

        # check if a list of channels has been provided. If not then just use
        # all channels.
        if channels:
            self.channels = channels
        else:
            self.channels = range(16)

        # Configure all FIO pins to be analog
        # FIO pins are located on LabJack
        # for U3-HV, FI00-03 are equivalent to AIN0-3
        print "Configuring FI00-07 as analog inputs"
        self.d.writeRegister(FIO_ANALOG, 255)

        # Configure all EIO pins to be analog
        print "Configuring EI00-07 as analog inputs"
        self.d.writeRegister(EIO_ANALOG, 255)

        # make a list of read commands
        self.cmd = []
        for ch in self.channels:
            self.cmd.append(u3.AIN(ch, 31,
                                    QuickSample = False,
                                    LongSettling = False))

    def configureStream(self, streamIndex):

        # In case the stream was left running from a previous execution
        try: self.d.streamStop()
        except: pass

        self.d.streamConfig( NumChannels = self.numChannels,
            PChannels = [ self.streamChannels[streamIndex] ],
            NChannels = [ 31 ],
            Resolution = self.resolution,
            SampleFrequency = self.sampleFrequency )

        print "AIN0%d" % self.streamChannels[streamIndex] + " configured for stream"

    def initTrigger(self):
        # The trigger is by default set to the high=1, but we'll ensure it's an input
        self.d.getFeedback(u3.BitDirWrite(IONumber = self.triggerChannel, Direction = 0))
        print "CIO channel configured as streamTrigger"
        #print "state%d" % self.d.getFeedback(u3.BitStateRead(IONumber = self.triggerChannel))[0]
        #print "direction%d" % self.d.getFeedback(u3.BitDirRead(IONumber = self.triggerChannel))[0]


    def checkTrigger(self):
        return self.d.getFeedback(u3.BitStateRead(IONumber = self.triggerChannel))[0]

    def startStream(self):
        print "Stream Started"
        self.d.streamStart()
        #t = 0 is defined as the first data point collected
        self.start = 0.0

    def stopStream(self):
        print "Stream Stopped"
        self.d.streamStop()
        self.start = 0.0

    def streamMeasure(self):
        try:
            for r in self.d.streamData():
                if r is not None:
                    if r['errors'] or r['numPackets'] != self.d.packetsPerRequest or r['missed']:
                        print "error: errors = '%s', numpackets = %d, missed = '%s'" % (r['errors'], r['numPackets'], r['missed'])

                        #cnt = 0
                        # # StreamData packets are 64 bytes and the 11th byte is the error code.
                        # # Iterating through error code bytes and displaying the error code
                        # # when detected.
                        #for err in r['result'][11::64]:
                            #errNum = ord(err)
                            #if errNum != 0:
                                #print "Packet", cnt, "error:", errNum
                            #cnt+=1
                break
        finally:
            pass
        return r

    def streamWrite(self, r, streamIndex):
        if r is not None:
            chans = [ r['AIN%d' % self.streamChannels[streamIndex]] ]
            #t = 0 is defined as the first data point collected
            datapoint = 0.0
            beginScan = self.start
            tbd = 1.0 / self.sampleFrequency #time between datapoints in seconds
            for i in range(len(chans[0])):
                self.streamHold.write( "\t".join( ['%.6f' % c[i] for c in chans] ) + '\t' + '%0.7f' % (beginScan + datapoint*tbd) + '\n' )
                datapoint += 1.0

            self.start += datapoint*tbd
        else:
            self.streamHold.write("empty")

    def initStringStream(self):
        self.streamHold = cStringIO.StringIO()

    def streamHeader(self, streamIndex):
        self.streamHold.write("AIN0%d" % self.streamChannels[streamIndex] + '\t' + "Time(s)\n")

    def filePush(self):
        data = self.streamHold.getvalue()

        writeTime = datetime.now()
        today = str(writeTime.date())
        #Create directory in which to store todays data
        if not os.path.exists(self.streamFolder+today):
            os.makedirs(self.streamFolder+today)
        #This is now our directory to write in
        todayFolder = self.streamFolder+today+'/'
        #And our file to write in is the time
        streamFile = todayFolder+time.strftime('%H_%M_%S')
        currentFile = open(streamFile, 'a')

        #Write all data to file
        currentFile.write(data)
        #Close stringStream and free the memory buffer
        self.streamHold.close()

    def closeLJ(self):
        self.d.close()

    def read(self, averages=1):
        bits =  self.d.getFeedback(self.cmd)
        voltage = [0.0]*len(bits)
        for j in range(averages):
            for ch, bit, i in zip(self.channels, bits, range(len(bits))):
                if ch<4:
                    LV = False
                else:
                    LV = True
                voltage[i] += 1000.0*self.d.binaryToCalibratedAnalogVoltage(bit,
                          isLowVoltage = LV,
                          isSingleEnded = True, isSpecialSetting = False,
                          channelNumber = ch)
        for i in range(len(voltage)):
            voltage[i] = voltage[i]/averages
        return voltage

    def getChannels(self):
        if self.channels:
            return self.channels
        else:
            return None

    def getAllChannels(self):
        return self.all_channels
