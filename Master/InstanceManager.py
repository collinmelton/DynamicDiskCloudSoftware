'''
Created on Jul 25, 2014

@author: cmelton
'''
import os, subprocess, time, pickle, sys, csv

# add GCE project to path
from InstanceData import *

class InstanceManager(object):
    '''
    This class manages instances by sshing into the instance to get relevant data, such as
    data about whether the instance is completed and what its memory/cpu usage is.
    '''

    def __init__(self, myDriver, instances, instanceStorageDirectory, log, rootdir):
        '''
        Constructor
        '''
        self.myDriver=myDriver
        self.instances=instances
        self.instanceStorageDirectory=instanceStorageDirectory
        self.instanceInfo={} # maps instances to most recent status
        self.log = log
        self.rootdir=rootdir
    
    # retrieves instance data via scp
    def retrieveInstanceData(self, instance_name):
        self.log.write("retrieving instance data for "+instance_name)
        myfile=self.rootdir+"StartupCommandHistoryv2.pickle"
        destination=os.path.join(self.instanceStorageDirectory, instance_name+".history.pickle")
        errored=True
        i=0
        while errored:
#             errored=(subprocess.call(['gcutil', 'pull', instance_name, myfile, destination])!=0)
            errored=(subprocess.call(['scp', '-o', 'stricthostkeychecking=no', instance_name+":"+myfile, destination])!=0)
            if errored:
                i+=1
                if i==3: 
                    destination=None
                    break
                self.log.write("error retrieving instance data for "+instance_name)
                time.sleep(10*i)
        self.instanceInfo[instance_name]=destination
    
    # retrieve old instance info from disk if it exists
    def retrieveOldInstanceData(self, instance_name):
        destination=os.path.join(self.instanceStorageDirectory, instance_name+".history.pickle")
        if os.path.exists(destination):
            self.instanceInfo[instance_name]=destination
            self.log.write("loading instance data from disk for "+instance_name)
            return True
        return False
    
    # returns loaded instance data object as instance of InstanceData
    def loadInstanceData(self, instance_name):
#         f=open(self.instanceInfo[instance_name], 'r')
#         savedData=pickle.load(f)
#         f.close()
        return InstanceData(instance_name, "None", self.instanceInfo[instance_name])

    # get status of instance
    def getInstanceStatus(self, instance_name):
        # if already complete don't bother
        if self.instances[instance_name].status=="complete": return "complete"
        # if not started don't bother trying to get instance data via ssh
        if not self.instances[instance_name].created: 
            # check if instance data around from previous run
            if not self.retrieveOldInstanceData(instance_name):
                return "not started"
        else:
            # retrieve instance info via ssh
            self.retrieveInstanceData(instance_name)
        # if couldn't retrieve instance data
        if self.instanceInfo[instance_name]==None: 
            return "ssh error"
        # load instance data and retrieve status
        d=self.loadInstanceData(instance_name)
#         print d.status()
#         print d.summary()
        return d.status()
    
    def printInstanceDataToCSV(self, pickleDirectory, filenamebase):
        perf_csvfile = open("performance_"+filenamebase+".csv", 'wb')
        perf_datawriter = csv.writer(perf_csvfile)
        com_csvfile = open("commands_"+filenamebase+".csv", 'wb')
        com_datawriter = csv.writer(com_csvfile)
        pickleFiles=[]
        for p in os.listdir(pickleDirectory):
            if ".pickle" in p: pickleFiles.append(p)
        first=True
        for p in pickleFiles:
            i = InstanceData(p.strip(".pickle"), "None", p)
            lines= i.performance_to_table(first)
            for line in lines: perf_datawriter.writerow(line)
            lines= i.commands_to_table(first)
            for line in lines: com_datawriter.writerow(line)
            first=False
        perf_csvfile.close()
        com_csvfile.close()