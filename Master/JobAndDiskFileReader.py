'''
Created on Jul 25, 2014

@author: cmelton
'''

from Disks import Disk
from Instances import Instance
import csv, time, sys

# some global variables
DEFAULT_DISK_PARAMS={"image":None, "location":"us-central1-a", "snapshot":None}
DEFAULT_INSTANCE_PARAMS={"size":"n1-standard-1", "image":None, "location":"us-central1-a", 
                         "ex_network":"default", "ex_tags":[], "ex_metadata":{'items': []}}

class JobAndDiskFileReader(object):
    '''
    This class reads in job and and disk info.
    '''
    
    def __init__(self, job_csv_file, disk_csv_file, myDriver, log, rootdir, StackdriverAPIKey="", activateStackDriver=False):
        self.job_csv_file=job_csv_file
        self.disk_csv_file=disk_csv_file
        self.myDriver=myDriver
        self.log=log
        self.rootdir=rootdir,
        self.StackdriverAPIKey = StackdriverAPIKey,
        self.activateStackDriver= activateStackDriver
    
    def trycommand(self, func, *args, **kwargs):
        retries = 10
        tries = 0
        while tries<retries:
            try:
                x = func(*args, **kwargs)
                return x
            except:
                e = sys.exc_info()[0]
                tries +=1
                time.sleep(10)
                print " Error: "+str(e)+ " try #"+str(tries) 
        return None
    
    # this function replicates variables in a column according to the $VARMULT variable 
    def __variable_mult(self, dataString, varString, sep="|", replacementString="$VARMULT"):
        if isinstance(dataString, str):
            vars=varString.split(sep)
            return "|".join(map(lambda x: dataString.replace(replacementString, "-"+x), vars))
        else:
            return dataString
    
    # this function replicates a dict replacing instances of variable $JOBMULT
    def __job_mult(self, newDiskInfo, varString, sep="|", replacementString="$JOBMULT", noDashReplacement="$JOBMULTNODASH"):
        vars=varString.split(sep)
        result=[]
        for var in vars:
            newDict={}
            for key in newDiskInfo:
                if newDiskInfo[key]==None or not isinstance(newDiskInfo[key], str):
                    newDict[key]=newDiskInfo[key]
                else:
                    stringToReplace=newDiskInfo[key].replace(noDashReplacement, var)
                    newDict[key]=stringToReplace.replace(replacementString, "-"+var.replace(" ", "-").lower())
            result.append(newDict)
        return result
    
    # replace job id
    def __job_id_rep(self, dataString, jobID, replacementString="$JOBID"):
        if isinstance(dataString, str): 
            return dataString.replace(replacementString, jobID+"-")
        else:
            return dataString
    
    def readDisks(self, DisksFile, myDriver, log):
        f = open(DisksFile, "rU")
        reader = csv.reader(f)
        header=reader.next()
        newDiskInfos=[]
        
        # find job_id, var_multiplicity, and job_multiplicity column indices
        job_id_col=header.index("job_id")
        #var_mult_col=header.index("var_multiplicity")
        job_mult_col=header.index("job_multiplicity")
        # read in disk info
        for row in reader:
            #var_mult=row[var_mult_col]
            job_mult=row[job_mult_col]
            job_id=row[job_id_col]
            self.jobids.add(job_id)
            newDiskInfo={}
            for i in range(len(row)):
                toadd=self.__job_id_rep(row[i], job_id) #replace job id var
                if toadd=="DEFAULT": toadd=DEFAULT_DISK_PARAMS[header[i]]
                newDiskInfo[header[i]]=toadd #_variable_mult(toadd, var_mult) # replace vars
            # replicate dicts for job multiplicity
            newDiskInfoList=self.__job_mult(newDiskInfo, job_mult)
            for newDiskInfo in newDiskInfoList: 
                newDiskInfos.append(newDiskInfo)
        f.close()
        
        # make disk instances
        result={}
        for newDiskInfo in newDiskInfos:
            result[newDiskInfo['name']]=Disk(newDiskInfo['name'], newDiskInfo['size'], 
                                                   newDiskInfo['location'], newDiskInfo['snapshot'], 
                                                   myDriver, newDiskInfo['image'], [], log, disk_type = newDiskInfo['disk_type']) 
        return result
    
    def readInstances(self, InstancesFile, myDriver, disks, log):
        f = open(InstancesFile, "rU")
        reader = csv.reader(f)
        header=reader.next()
        
        # find job_id, var_multiplicity, and job_multiplicity column indices
        job_id_col=header.index("job_id")
        var_mult_col=header.index("var_multiplicity")
        job_mult_col=header.index("job_multiplicity")
        
        newInstInfos=[]
        for row in reader:
            var_mult=row[var_mult_col]
            job_mult=row[job_mult_col]
            job_id=row[job_id_col]
            self.jobids.add(job_id)
            newInstInfo={}
            for i in range(len(row)):
                toadd=self.__job_id_rep(row[i], job_id) #replace job id var
                if toadd=="DEFAULT": toadd=DEFAULT_INSTANCE_PARAMS[header[i]]
                newInstInfo[header[i]]=self.__variable_mult(toadd, var_mult) # replace vars
            # replicate dicts for job multiplicity
            newInstInfosList=self.__job_mult(newInstInfo, job_mult)
            for newInstInfo in newInstInfosList: 
                newInstInfos.append(newInstInfo)
        f.close()
        # make instances of each instance
        result={}
        for newInstInfo in newInstInfos:
            if newInstInfo["run"]=="TRUE":
                # get standard node params
                node_params={}
                for param in ["size", "image", "location", "ex_network"]:
                    node_params[param]=newInstInfo[param]
                # parse ex_tags
                if newInstInfo["ex_tags"]!=DEFAULT_INSTANCE_PARAMS["ex_tags"]:
                    newInstInfo["ex_tags"]=newInstInfo["ex_tags"].split("|")
                node_params["ex_tags"]=newInstInfo["ex_tags"]
                # parse ex_metadata and add to node params
                if newInstInfo["ex_metadata"]!=DEFAULT_INSTANCE_PARAMS["ex_metadata"]:
                    ex_metadata={'items': []}
                    for pair in newInstInfo["ex_metadata"].split("|"):
                        if pair!="":
                            key, value= pair.split(":")
                            ex_metadata["items"].append({"key":key, "value":value})
                    node_params["ex_metadata"]=ex_metadata
                else:
                    node_params["ex_metadata"]=newInstInfo["ex_metadata"]
                # get read disks and boot disk
                read_disks=[]
                for rd in newInstInfo["read_disks"].split("|"):
                    if rd !="":
                        if rd not in disks: raise Exception("read disk not found:"+rd) 
                        read_disks.append(disks[rd])
                        disks[rd].addInstance(newInstInfo['name'])
                read_write_disks=[]
                for rd in newInstInfo["read_write_disks"].split("|"):
                    if rd !="":
                        if rd not in disks: raise Exception("read/write disk not found:"+rd) 
                        read_write_disks.append(disks[rd])
                        disks[rd].addInstance(newInstInfo['name'])
                if newInstInfo["boot_disk"] not in disks: raise Exception("boot disk not found:"+newInstInfo["boot_disk"])
                boot_disk=disks[newInstInfo["boot_disk"]]
                boot_disk.addInstance(newInstInfo['name'])
                # parse dependency names
                newInstInfo['dependencies']=newInstInfo['dependencies'].split("|")
                if newInstInfo['dependencies']==[""]:
                    newInstInfo['dependencies']=[]
                # add new instance
                print self.activateStackDriver
                result[newInstInfo['name']]=Instance(newInstInfo['name'], node_params,
                                                     newInstInfo['dependencies'],
                                                     read_disks, read_write_disks, boot_disk, myDriver,
                                                     newInstInfo['script'], log, self.rootdir, preemptible=("T" in newInstInfo['preemptible']),
                                                     activateStackDriver = self.activateStackDriver, 
                                                     StackdriverAPIKey = self.StackdriverAPIKey)
        return result
    
    def readInJobInfo(self):
        self.jobids = set()
        disks=self.readDisks(self.disk_csv_file, self.myDriver, self.log)
        existentDisks=None
        while existentDisks==None: 
            existentDisks=[]
            for id in self.jobids:
                existentDisks+=self.trycommand(self.myDriver.list_volumes, regex=".*"+id+".*")
        for disk in disks:
            disks[disk].setDisk(existentDisks)
        instances=self.readInstances(self.job_csv_file, self.myDriver, disks, self.log)
        existentNodes = None
        while existentNodes == None:
            existentNodes=[]
            for id in self.jobids:
                existentNodes+=self.trycommand(self.myDriver.list_nodes, regex=".*"+id+".*")
        for instance in instances:
            instances[instance].setInstances(existentNodes)
        return instances, disks
