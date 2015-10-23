'''
Created on Jul 25, 2014

@author: cmelton
'''

from JobAndDiskFileReader import JobAndDiskFileReader
from InstanceManager import InstanceManager 

class JobManager(object):
    '''
    This class manages the jobs and instances.
    '''
    def __init__(self, job_csv_file, disk_csv_file, myDriver, log, storage_directory, max_instances, rootdir, update=True, StackdriverAPIKey="", activateStackDriver=False):
        '''
        Constructor
        '''
        self.job_csv_file=job_csv_file
        self.disk_csv_file=disk_csv_file
        self.myDriver=myDriver
        self.log=log
        jobInfoReader=JobAndDiskFileReader(job_csv_file, disk_csv_file, myDriver, log, rootdir, StackdriverAPIKey=StackdriverAPIKey, activateStackDriver=activateStackDriver)
        self.instances, self.disks = jobInfoReader.readInJobInfo()
        self.instanceManager=InstanceManager(myDriver, self.instances, storage_directory, log, rootdir)
        self.running_instances=0
        self.max_instances=max_instances
        if update:
            self.updateJobStatus()
            self.updateRunningInstanceCount()
    
    def updateRunningInstanceCount(self):
        self.running_instances=sum([1 for inst in self.instances.values() if inst.created and not inst.destroyed])
#         print self.running_instances, "jobs running"
#         for j in self.instances:
#             print j, self.instances[j].created, self.instances[j].destroyed
        
    # returns true if jobs remain, false otherwise
    def remainingJobs(self):
        for job in self.instances:
            if (not self.instances[job].started()) and (not self.instances[job].destroyed and not self.instances[job].status in ["failed", "gce error"]): return True
        return False
    
    # starts all jobs that are ready to run
    def startNewJobs(self):
        self.updateRunningInstanceCount()
        for job in self.instances:
            if self.running_instances < self.max_instances:
                if self.instances[job].startIfReady(self.instances):
                    self.running_instances+=1
                
    # this function updates the status of all jobs
    def updateJobStatus(self):
        for job in self.instances:
            self.instances[job].updateStatus(self.instanceManager)
    
    # this function writes a table with a summary of disks and instances to the log file
    def writeInstanceSummary(self):
        writeHeader=True
        self.log.writeRaw("Instance Summary:\n")
        for instance in self.instances:
            summary=self.instances[instance].tabDelimSummary()
            if writeHeader:
                self.log.writeRaw(summary["header"])
                writeHeader=False
            self.log.writeRaw("\n"+summary["values"])
        writeHeader=True
        self.log.writeRaw("Disk Summary:\n")
        for disk in self.disks:
            summary=self.disks[disk].tabDelimSummary()
            if writeHeader:
                self.log.writeRaw(summary["header"])
                writeHeader=False
            self.log.writeRaw("\n"+summary["values"])

    
    def waitForCompletion(self):
        for instance_name in self.instances:
            self.instances[instance_name].waitForCompletion(self.instanceManager)
                
    def shutDown(self, wait=True):
        # wait for all instances to be done
        if wait: 
            self.waitForCompletion()
            # shut down any remaining instances
            for instance in self.instances:
                if (self.instances[instance].status=="complete" or self.instances[instance].status=="failed"):
                    self.instances[instance].destroy()
        else:
            for instance in self.instances: self.instances[instance].destroy(force = True)
        # shut down anay remaining disks
        for disk in self.disks:
            self.disks[disk].destroy()
        