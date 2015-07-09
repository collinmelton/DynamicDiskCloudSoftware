from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import time, sys

USERID="cmelton"

# This class represents a google instance that will be run in the future
class Instance:
    def __init__(self, name, node_params, depedencies, read_disks, read_write_disks, boot_disk, myDriver, script, log, rootdir, scriptAsParam=True):
        self.name=name
        self.node_params=node_params
        self.dependencyNames=depedencies
        self.read_disks=read_disks
        self.read_write_disks=read_write_disks
        self.boot_disk=boot_disk
        self.myDriver=myDriver
        self.created=False
        self.destroyed=False
        self.script=script
        self.node=None
        self.log=log
        self.scriptAsParam=scriptAsParam
        self.failed=False
        self.printToLog("initialized instance class")
        self.status="not started"
        self.rootdir=rootdir
        self.ssh_error_counter = 0

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

    def updateStatus(self, instanceManager):
        if self.status=="started" or self.status=="ssh error" or self.status=="not started":
            self.__updateStatus(instanceManager)

    def manual_restart(self):
        self.destroy(instances=None, destroydisks=False, force = False)
        self.create()
        
    def restart(self):
        result = self.trycommand(self.myDriver.reboot_node, self.node)
        if result == None:
            self.manual_restart()
        self.printToLog("created instance on GCE")
        self.created=True
        self.failed=False
        self.destroyed=False
        self.status="started"

    # update status and destroy if complete
    def __updateStatus(self, instanceManager):
        self.status = self.trycommand(instanceManager.getInstanceStatus, self.name)
        if self.status == "ssh error":
            self.ssh_error_counter +=1
            self.printToLog("recurrent ssh error on "+self.name+", count="+str(self.ssh_error_counter))
            if self.ssh_error_counter == 2: 
                self.printToLog("setting status of "+self.name+" to gce error")
                self.restart()
            if self.ssh_error_counter == 4:
                self.status = "gce error"
        if self.status=="failed" or self.status == "gce error":
            self.created=True
            self.failed=True
            if not self.destroyed:
                self.destroy(instanceManager.instances, destroydisks=False)
        if self.status=="complete":
            self.created=True
            self.failed=False
            if self.node==None: self.destroyed=True
            if not self.destroyed:
                self.destroy(instanceManager.instances)

    def started(self):
        return self.created
    
    def waitForCompletion(self, instanceManager):
        if self.destroyed or not self.created: return
        while self.status!="complete" and self.status!="failed":
            time.sleep(60)
            self.updateStatus(instanceManager)
    
    def __dependenciesReady(self, jobs):
        for d in self.dependencyNames:
            if d in jobs:
                if not jobs[d].status=="complete":
                    self.printToLog(str(d)+" not ready")
                    return False
        return True

    # check if ready and if yes start job
    def startIfReady(self, jobs):
        # if already run do nothing
        if self.status=="complete": return False
        # if dependencies not ready do nothing
        if not self.__dependenciesReady(jobs): return False
        # if not created create and not failed its ready so create
        if not self.created and not self.failed:
            self.create()
            return True
        # if failed or other do nothing
        return False
#         # if had gce error restart
#         if self.status=="gce error" or self.status=="failed":
#             self.destroy()
#             self.create()
#             return True
        
            
    def setInstances(self, nodes):
        for node in nodes:
#             self.log.write(self.name+"|"+node.name)
            if node.name==self.name:
                self.node=node
                self.created=True
                self.failed=False
                self.destroyed=False
                self.status="started"
                self.log.write(self.name+"is already created!!")

    def tabDelimSummary(self):
        return {"header":"\t".join(["name", "node_params", "dependencyNames", "read_disks", 
                                    "boot_disk", "myDriver", "created", "destroyed", 
                                    "script", "node", "log", "scriptAsParam", "failed"]), 
                "values":"\t".join(map(lambda x: str(x), [self.name, self.node_params, self.dependencyNames, self.read_disks, 
                                                self.boot_disk, self.myDriver, self.created, self.destroyed, 
                                                self.script, self.node, self.log, self.scriptAsParam, self.failed]))}

    def printToLog(self, text):
        output=self.name+"\t"+text
        self.log.write(output)

    def toString(self):
        tabDelim=self.tabDelimSummary()
        return("\n".join([tabDelim["header"],tabDelim["values"]]))
#         return("\n".join(map(lambda x: "\t"+str(x), [self.name, self.node_params, self.dependencyNames, self.read_disks, 
#                                                 self.boot_disk, self.myDriver, self.created, self.destroyed, 
#                                                 self.script, self.node, self.log, self.scriptAsParam, self.failed])))
        

    
    def _mountDisksScript(self):
        read_only=map(lambda disk: disk.mount_script(False), self.read_disks)
        read_write=map(lambda disk: disk.mount_script(True), self.read_write_disks)
        result= "\n".join(read_only+read_write)
        return result
    
    def _unmountDisksScript(self):
        read_only=map(lambda disk: disk.unmount_script(), self.read_disks)
        read_write=map(lambda disk: disk.unmount_script(), self.read_write_disks)
        result= "\n".join(read_only+read_write)
        return result
    
    # package script in python script shell
    # the StartupWrapper.py program executes the script, saves the output to google cloud storage and updates the project meta data on start and completion
    def packageScript(self):
        script = self._mountDisksScript()+"\n"+self.script
        shutdownscript = self._unmountDisksScript()
        result = "\n#! /bin/bash"
#         result += "".join(map(lambda x: "\ngcutil cp gs://cmelton_wgs1/"+x+" /home/cmelton/GCE_Cluster/Worker/", ["InstanceData.py", "InstanceEngine.py", "Startup.py"]))
#         print result
        result += "\n/usr/local/bin/python2.7 "+self.rootdir+"DynamicDiskCloudSoftware/Worker/Startup.py --S \""+script.replace("\'", "'")+"\" --SD \""+shutdownscript.replace("\'", "'")+"\" --H /home/cmelton/StartupCommandHistoryv2.pickle --N "+self.name
        return(result)
    
    # create and run node on GCE
    def create(self):
        if not self.created: 
            #raise Exception('Trying to create already created instance on '+self.name)
            # make sure all necessary disks are created
            for disk in self.read_disks:
                if not disk.created:
                    disk.create()
            for disk in self.read_write_disks:
                if not disk.created:
                    disk.create()
            if self.boot_disk.disk != None:
                self.boot_disk.destroy()
            self.boot_disk.create()
            self.boot_disk.formatted=True # make sure to indicate that it is formatted because a boot disk will be formatted on startup
                
            # add startup script to metadata and make sure drive mounting is added to startup script
            if self.scriptAsParam:
                self.node_params["ex_metadata"]["items"].append({"key":"startup-script", "value":self.packageScript()})
            else:
                raise Exception("deploy with script form file or cloud storage not implemented yet")
#             print self.node_params["ex_metadata"]
            # change mode of disks and prepare them in a list for node creation
            for disk in self.read_disks:
                disk.mode="READ_ONLY"
            for disk in self.read_write_disks:
                disk.mode="READ_WRITE"
            additionalDisks=self.read_disks+self.read_write_disks
            # create node = GCE instance
            i=0
            while self.node==None:
                i+=1
                self.node=self.trycommand(self.myDriver.create_node, self.name, self.node_params["size"], self.node_params["image"], location=self.node_params["location"],
                                      ex_network=self.node_params["ex_network"], ex_tags=self.node_params["ex_tags"], ex_metadata=self.node_params["ex_metadata"], 
                                      ex_boot_disk=self.boot_disk.disk, serviceAccountScopes=["https://www.googleapis.com/auth/compute", "https://www.googleapis.com/auth/devstorage.read_write"], 
                                      additionalDisks=additionalDisks)
                if self.node==None:
                    self.node=self.trycommand(self.myDriver.ex_get_node, self.name)
                if i==2:
                    self.printToLog("failed to create instance on GCE")
                    break
            self.printToLog("created instance on GCE")
            self.created=True
            self.failed=False
            self.destroyed=False
            self.status="started"
        else: self.printToLog("instance already created on GCE")
    
    # destroy node on GCE
    def destroy(self, instances=None, destroydisks=True, force = False):
        # detatch disks and destroy if not needed
        for disk in self.read_disks:
            if not force: disk.detach(self)
            if destroydisks:
                disk.destroyifnotneeded(instances)
        for disk in self.read_write_disks:
            if not force: disk.detach(self)
            if destroydisks: 
                disk.destroyifnotneeded(instances)
            # self.myDriver.destroy_node(self.node)
        # destroy node
        if self.node!=None and not self.destroyed:
            self.trycommand(self.myDriver.destroy_node, self.node)
            self.node=None
            self.printToLog("destroyed instance on GCE")
            self.boot_disk.destroy()
            self.destroyed=True
            self.created=False
        else:
            self.printToLog("mistakenly trying to destroy "+self.name+", destroyed "+str(self.destroyed)+" self.node "+str(self.node==None))
            self.destroyed=True
            self.created=False
        

    def trycommand(self, func, *args, **kwargs):
        retries = 5
        tries = 0
        while tries<retries:
            try:
                x = func(*args, **kwargs)
                return x
            except:
                e = sys.exc_info()[0]
                tries +=1
                time.sleep(10)
                self.printToLog(str(func) + " Error: "+str(e)+ " try #"+str(tries)) 
        return None
                
                