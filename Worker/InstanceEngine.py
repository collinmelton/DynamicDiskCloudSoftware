'''
Created on Jul 25, 2014

@author: cmelton
'''

import time, InstanceData
from threading import Thread

class runCommands(Thread):
    '''
    This class represents a class that runs commands in sequence.
    '''
    def __init__(self, instanceData, shutdownData):
        super(runCommands, self).__init__()
        self.instanceData=instanceData
        self.shutdownData=shutdownData
    
    def runshutdown(self):
        command=self.shutdownData.nextCommand()
        while command !=None:
            command.run()
            command=self.shutdownData.nextCommand()

    def run(self):
        command=self.instanceData.nextCommand()
        while command !=None:
            failed=command.run()
            if failed: 
                self.runshutdown()
                self.instanceData.failed()
                return
            time.sleep(2)
            self.instanceData.save()
            command=self.instanceData.nextCommand()
        self.runshutdown()
        self.instanceData.command_data.commands+=self.shutdownData.command_data.commands
        self.instanceData.save()

class monitorPerformance(Thread):
    '''
    This class represents a class that cyclically monitors the machine performance characteristics
    at regular intervals defined by a period.
    '''
    def __init__(self, instanceData, period=1):
        super(monitorPerformance, self).__init__()
        self.instanceData=instanceData
        self.period=period
    
    def run(self):
        while not self.instanceData.finished():
            self.instanceData.updatePerformance()
            time.sleep(self.period)
        self.instanceData.updatePerformance()


class InstanceEngine(object):
    '''
    This class represents the main code for running scripts and monitoring the status of the 
    worker.
    '''
    def __init__(self, script_file, shutdown_file, history_file, name, period=10, performanceDataFile="perfData.tsv"):
        '''
        Constructor
        '''
        self.script_file=script_file
        self.history_file=history_file
        self.shutdown_file=shutdown_file
        self.name=name
        self.period=period
        self.performanceDataFile=performanceDataFile
        print self.script_file, self.history_file, self.name, self.period
        
    def run(self):
        self.instanceData=InstanceData.InstanceData(self.name, self.script_file, self.history_file)
        self.shutdownData=InstanceData.InstanceData(self.name, self.shutdown_file, self.history_file)

        # run commands
        task1 = monitorPerformance(self.instanceData, period=self.period)
        task2 = runCommands(self.instanceData, self.shutdownData)
        task1.daemon=True
        task2.daemon=True
        print "starting tasks"
        task1.start()
        task2.start()
        print "waiting for join"
        task1.join()
        task2.join()
        print "joined"
        print self.instanceData.summary()
        print "status:", self.instanceData.status()
        self.instanceData.writeSummaryToFile(self.performanceDataFile)
