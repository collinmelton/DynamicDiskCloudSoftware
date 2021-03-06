'''
Created on Jul 25, 2014

@author: cmelton

usage: python2.7 RunJobs.py --I test_instances.csv --D test_disks.csv --P yourprojectname --PM test.pem --E somelettersandnumbers@developer.gserviceaccount.com --RD /home/yourusername/ --SD ./

When run as main this program will boot a cloud compute workflow as specified in test_disks.csv and test_instances.csv. 

'''
from optparse import OptionParser
import LogFile, time, imp, os
from GCEManager import GCEManager
from JobManager import JobManager

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--I", dest = "InstancesFile", help = "this specifies a csv files with information about the instances to boot in this workflow",
                      metavar = "FILE", type = "string", default = "./test_instances.csv")
    parser.add_option("--D", dest = "DisksFile", help = "this specifies a csv file with information about the disks to boot in this workflow",
                      metavar = "FILE", type = "string", default = "./test_disks.csv")
    parser.add_option("--L", dest = "logFilePath", help = "path/name of log file to be output"+
                      "concurrently", metavar = "FILE", default = "logFileTest.txt", type = "string")
    parser.add_option("--E", dest = "serviceAccountEmail", help = "service account email address", 
                      metavar = "STRING", 
                      default = "", 
                      type = "string")
    parser.add_option("--AA", dest="authAccount", help = "auth account for gcloud access, needs to be a listed account with gcloud auth list on all instance images, when worker nodes start this account will be set as the active account",
                      metavar = "STRING")
    parser.add_option("--P", dest = "projectID", help = "Google project ID", metavar = "STRING", 
                      default = "gbsc-gcp-lab-snyder",  
                      type = "string")
    parser.add_option("--PM", dest = "pemFile", help = "path to pem file for service account", 
                      metavar = "FILE", default = "", 
                      type = "string")
    parser.add_option("--DC", dest = "dataCenter", help = "name of default data center", metavar = "STRING",
                       default = "us-central1-a", type = "string")
    parser.add_option("--A", dest = "authType", help = "authorization type", metavar = "STRING", 
                      default = "SA", type = "string")
    parser.add_option("--M", dest = "metadataURL", help = "metadata url", metavar = "STRING", 
                      default = 'http://metadata/computeMetadata/v1/', type = "string")
    parser.add_option("--SD", dest = "storageDirectory", help = "storage directory for instance data files",
                      metavar = "STRING", default = './TestData', type = "string")
    parser.add_option("--MI", dest = "maxInstances", help = "max # of concurrent instances",
                      metavar = "STRING", default = '22', type = "string")
    parser.add_option("--HR", dest = "hardRestart", help = "if T shut down all current instances and disks",
                      metavar = "STRING", default = 'F', type = "string")
    parser.add_option("--RD", dest = "rootdir", help = "directory of cloud software project on worker instances",
                      metavar = "STRING", type = "string")
    parser.add_option("--SDAPI", dest = "StackdriverAPIKey", help = "stackdriver API key",
                      metavar = "STRING", default = '', type = "string")
    parser.add_option("--ASD", dest = "activateStackDriver", help = "whether to activate stackdriver on all instances, enter 'T' for True",
                      default = "F", metavar = "STRING", type = "string")
    (options, args) = parser.parse_args()
    return options

class JobExecutionLoop(object):
    '''
    This class executes jobs from a job queue taking into account dependencies.
    '''

    def __init__(self, log_file, job_csv_file, disk_csv_file, service_account_email_address, 
                 project_id, pem_file, data_center, auth_type, metadata_url, storage_directory, rootdir, auth_account, cycle_period=60, max_instances=23, restart=False, 
                 commandFile = "", StackdriverAPIKey="", activateStackDriver=False):
        '''
        Constructor
        '''
        self.log_file=log_file
        self.job_csv_file=job_csv_file
        self.disk_csv_file=disk_csv_file
        self.service_account_email_address=service_account_email_address
        self.pem_file=pem_file
        self.project_id=project_id
        self.data_center=data_center
        self.auth_type=auth_type
        self.metadata_url=metadata_url
        self.cycle_period=cycle_period
        self.storage_directory=storage_directory
        self.max_instances = max_instances
        self.restart=restart
        self.commandFile = commandFile
        self.rootdir=rootdir
        self.auth_account=auth_account
        self.StackdriverAPIKey = StackdriverAPIKey
        self.activateStackDriver = activateStackDriver
        
    def run(self):
        # get logfile reader
        self.log = LogFile.LogFile(self.log_file)
    
        # get google compute engine driver to interact with the compute engine
        self.myDriver= GCEManager(self.service_account_email_address, self.pem_file, self.auth_account, project=self.project_id)
        
        # start job manager, which has some useful functions for checking on the status and starting jobs
        self.jobManager=JobManager(self.job_csv_file, self.disk_csv_file, self.myDriver, self.log, self.storage_directory, self.max_instances, 
                                   self.rootdir, update= (not self.restart), StackdriverAPIKey=self.StackdriverAPIKey, activateStackDriver=self.activateStackDriver)

        # hard restart if restart is true to remove previous instances and disks
        if self.restart: 
            self.log.write("performing hard reset of all running instances and disks")
            self.jobManager.shutDown(wait=False)
            # need to reboot manager too so it knows the jobs are gone
            self.jobManager=JobManager(self.job_csv_file, self.disk_csv_file, self.myDriver, self.log, self.storage_directory, self.max_instances, 
                                       self.rootdir, StackdriverAPIKey=self.StackdriverAPIKey, activateStackDriver=self.activateStackDriver)

        # run jobs
        while(self.jobManager.remainingJobs()):
            print "updating job status for all jobs"
            self.jobManager.updateJobStatus()
            print "starting new jobs"
            self.jobManager.startNewJobs()
            print "waiting for jobs to complete"
            time.sleep(self.cycle_period) # cycle every min or whatever is specified
        self.jobManager.writeInstanceSummary()
        
        # clean up
        self.jobManager.shutDown()
  

if __name__ == '__main__':
    options = getOptions()
    print options.rootdir
    print options.activateStackDriver
    engine=JobExecutionLoop(options.logFilePath, options.InstancesFile, options.DisksFile,
                            options.serviceAccountEmail, options.projectID, options.pemFile, 
                            options.dataCenter, options.authType, options.metadataURL, 
                            options.storageDirectory, options.rootdir, options.authAccount, max_instances=int(options.maxInstances),
                            restart=(options.hardRestart=='T'), StackdriverAPIKey=options.StackdriverAPIKey, 
                            activateStackDriver=(options.activateStackDriver=="T"))
    engine.run()
    
  