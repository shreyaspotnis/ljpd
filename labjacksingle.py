"""Implements a class to conveniently get single measurements from LabjackU3."""

import u3, LabJackPython
from time import sleep
from datetime import datetime
import struct
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

    def getConfig(self):
        #get stream settings from config.ini
        self.streamChannel = self.config.getint('stream_settings','streamChannel')
        self.triggerChannel = self.config.getint('stream_settings','triggerChannel')
        self.sampleFrequency = self.config.getint('stream_settings','sampleFrequency')
        self.resolution = self.config.getint('stream_settings','resolution')
        self.numChannels = self.config.getint('stream_settings','numChannels')
        self.streamFile = self.config.get('stream_settings', 'streamFile')
        
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

    def configureStream(self):
        # In case the stream was left running from a previous execution
        try: self.d.streamStop()
        except: pass

        self.d.streamConfig( NumChannels = self.numChannels,
            PChannels = [ self.streamChannel ],
            NChannels = [ 31 ],
            Resolution = self.resolution,
            SampleFrequency = self.sampleFrequency )

        # set one channel to be the trigger for the stream
        #self.d.configIO(TimerCounterPinOffset = 6, NumberOfTimersEnabled = 1)
        #self.d.getFeedback(u3.BitDirWrite(IONumber = trigChan, Direction = 0))

    def checkStreamTrig(self):
        return self.d.getFeedback(u3.BitStateRead(IONumber = self.triggerChannel))

    def streamMeasure(self):
        try:
            for r in self.d.streamData():
                if r is not None:
                    if r['errors'] or r['numPackets'] != self.d.packetsPerRequest or r['missed']:
                        print "error: errors = '%s', numpackets = %d, missed = '%s'" % (r['errors'], r['numPackets'], r['missed'])
                        cnt = 0

                        # # StreamData packets are 64 bytes and the 11th byte is the error code.
                        # # Iterating through error code bytes and displaying the error code
                        # # when detected.
                        # for err in r['result'][11::64]:
                        #     errNum = ord(err)
                        #     if errNum != 0:
                        #         print "Packet", cnt, "error:", errNum
                        #     cnt+=1
                break
        finally:
            pass
        return r

    def streamWrite(self, r):
        self.streamFile.write(r['AIN%d'] % self.streamChannel + '\n')

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
