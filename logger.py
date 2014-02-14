import sys
import os
import re
import numpy as np
from datetime import datetime

class Logger():

    def __init__(self, config, channel_labels):
        self.skip = config.getint('settings','LOG_SKIP')
        self.folder = config.get('settings', 'LOG_FOLDER')
        self.write_interval = config.getint('settings', 'LOG_WRITE_INTERVAL')
        self.log_max = config.getint('settings', 'LOG_MAX')
        self.snapshot_file = config.get('settings', 'LOG_SNAPSHOT_FILE')
        self.snapshot_average = config.getint('settings', 'LOG_SNAPSHOT_AVERAGE')

        # We haven't written data anytime
        self.last_write_time = datetime.now()
        
        # make header for the log files
        # create a dictionary containing all the data
        self.channel_labels = channel_labels
        self.header = '#Time ms '
        self.logspace = []
        self.logdict = {}
        for i in range(16):
            ch_name = 'AIN'+str(i)
            self.header+=channel_labels[i]+'('+ch_name+') '
            self.logspace.append(np.zeros(self.log_max))
            self.logdict[ch_name] = self.logspace[i]
            self.logdict[channel_labels[i]] = self.logspace[i]
        self.header+='\n'
        
        self.n_log_curr = 0  # gives the index where we want to log data
        
        # add a 'time' array in our dictionary, 
        self.logdict['time'] = np.arange(self.log_max)

        # initialize the data list
        self.data = []
        self.log_times = []

        # get today's date, which is also the filename
        self.today = str(self.last_write_time.date())

        # check if the file already exists
        file_exists = os.path.isfile(self.folder+self.today)

        self.f = open(self.folder+self.today, 'a')

        # write the header on the file
        if not file_exists:
            self.f.write(self.header)
        self.f.close()

        # number of skipped steps
        self.n_skip = 0

    def write(self):
        # get the current time
        curr_time = datetime.now()

        # check if we need to open a new file for writing
        if curr_time.date() != self.last_write_time.date():
            # its a new day! open a new file
            self.today = str(curr_time.date())
            print "Its a new day ", self.today
            self.f = open(self.folder+self.today, 'a')

            # write the header
            self.f.write(self.header)
        else:
            self.f = open(self.folder+self.today, 'a')
        
        # write data
        if len(self.data) > 0:
            # insert the time
            self.f.write(str(curr_time.time())+' ')

            # count the total number of milliseconds since the start of the day
            total_ms = ((curr_time.hour*60+curr_time.minute)*60
                        +curr_time.second)*1000+curr_time.microsecond/1000
            self.f.write(str(total_ms)+' ')
            dnp = np.array(self.data)
            #take average of all data collected till now
            dataavg = np.mean(dnp, 0)
            for d in dataavg:
                self.f.write('{0:.2f}'.format(d)+' ')
            self.f.write('\n')

        self.last_write_time = curr_time
        self.f.close()

    def log(self, voltages):
        # check if its time to write
        if self.n_skip % self.skip == 0:
            self.write()
            # clear the data cache
            self.data = []
        for i in range(16):
            self.logspace[i][self.n_log_curr] = voltages[i]
        self.n_log_curr = (self.n_log_curr+1) % self.log_max
        self.data.append(voltages)
        self.log_times.append(datetime.now())
        self.n_skip += 1

    def savesnapshot(self, voltages, comment):
        # get the current time
        snapshot_time = datetime.now()

        fp = open(self.snapshot_file, 'a')
        
        fp.write(str(snapshot_time.date())+'\t'+str(snapshot_time.time())+'\t')
        for v in voltages:
            fp.write('{0:.2f}'.format(v)+'\t')

        # since we will be writing all the comments onto one line, we do not
        # want to insert newlines, hence just replace \n with something else
        fp.write(re.sub('\n', '<newline>', comment))
        fp.write('\n')

        fp.close()

    def loadsnapshot(self):
        fp = open(self.snapshot_file, 'r')
        done = False

        snap_date = []
        snap_time = []
        snap_data = []
        snap_comment = []

        while 1:
            s = fp.readline()
            if s == '':
                break

            sp = s.split('\t')
            
            snap_date.append(sp[0])
            snap_time.append(sp[1])
            
            dat = []
            for i in range(2, 18):
                dat.append(float(sp[i]))
            snap_data.append(dat)
        
            comment = re.sub('<newline>', '\n', sp[18])
            snap_comment.append(comment)

        return snap_date, snap_time, snap_data, snap_comment

