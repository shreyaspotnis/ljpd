# David Spierings, Jan. 19 2015
# Adapted from Peter N. Saeta, 2013 November 11

# This code uses the LabJack to record 1 or more voltages at a
# regular cadence. It runs until you stop it with Ctrl-C.
# Edit the values below (above the import u3 statement)
# to match your requirements. Note that the Resolution parameter
# sets the accuracy of the data. The smaller the number, the better
# the accuracy, but the slower the sampling rate must be. See
# http://labjack.com/support/u3/users-guide/3.2 for details.

NumChannels = 1
# The number of times each second that each channel will be sampled
SampleFrequency = 10000
Resolution = 1
# Where the data will be written
filename = 'data.txt'
# Put a list of strings with the names you would like associated with
# chan0, chan1, ... Example: wavenames = ['sync', 'V_in', 'V_out']
# If left blank, it will be filled with ['wave0', 'wave1', ...]
wavenames = []

import u3
import time

# Prepare the u3 interface for streaming

d = u3.U3()        # initialize the interface; assumes a single U3 is plugged in to a USB port
d.configU3()    # set default configuration
d.configIO( FIOAnalog = 1 )        # ask for analog inputs
d.getFeedback(u3.BitDirWrite(IONumber = 6, Direction = 0))        # set FI06 as digital input

# In case the stream was left running from a previous execution
try: d.streamStop()
except: pass


d.streamConfig( NumChannels = NumChannels,
    PChannels = range(NumChannels),
    NChannels = [ 31 for x in range(NumChannels) ],
    Resolution = Resolution,
    SampleFrequency = SampleFrequency )

#d.packetsPerRequest = 1000

# Try to measure a data set.
def measure():
    try:
        for r in d.streamData():
            if r is not None:
                if r['errors'] or r['numPackets'] != d.packetsPerRequest or r['missed']:
                    print "error: errors = '%s', numpackets = %d, missed = '%s'" % (r['errors'], r['numPackets'], r['missed'])
                break
    finally:
        pass
    return r

# Write a set of data to the file
def writeData( r ):
    chans = [ r['AIN%d' % (n)] for n in range(NumChannels) ]
    for i in range(len(chans[0])):
        f.write( "\t".join( ['%.6f' % c[i] for c in chans] ) + '\n' )

with open(filename, 'w') as f:
    f.write( "frequency=%d\n" % SampleFrequency)
    if wavenames == []:
        wavenames = ['wave%d' % n for n in range(NumChannels)]
    f.write( '\t'.join(wavenames) + '\n')

# start the stream
d.streamStart()
loop = 0
# Set tigger, which will initiate data writing
inputState = d.getDIState(6)
print inputState

try:
    start = time.time()
    while True:
        with open(filename, 'a') as f:
            writeData( measure() )
        loop += 1
        print( "[%.4d %.2f s]" % (loop, time.time() - start))
finally:
    d.streamStop()