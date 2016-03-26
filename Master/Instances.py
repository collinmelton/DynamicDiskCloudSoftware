from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import time, sys

USERID="cmelton"

# This class represents a google instance that will be run in the future
class Instance:
    def __init__(self, name, node_params, depedencies, read_disks, read_write_disks, boot_disk, myDriver, script, log, 
                 rootdir="/home/cmelton/", scriptAsParam=True, preemptible=True, StackdriverAPIKey="",
                 activateStackDriver=False, numLocalSSD=0, localSSDInitSources="", localSSDDests=""):
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
        self.preemptible = preemptible
        self.activateStackdriver = activateStackDriver
        self.StackdriverAPIKey = StackdriverAPIKey
        self.numLocalSSD = numLocalSSD
        self.localSSDInitSources = localSSDInitSources
        self.localSSDDests = localSSDDests
#         if self.numLocalSSD > 0: self.preemptible = False # no preemptible for local ssd for now

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

    def updateStatus(self, instanceManager):
        if self.status=="started" or self.status=="ssh error" or self.status=="not started":
            self.__updateStatus(instanceManager)

    def manual_restart(self):
        self.printToLog("performing manual restart")
        self.destroy(instances=None, destroydisks=False, force = False)
        for node in self.myDriver.list_nodes():
            self.printToLog(str(node.__dict__)) 
        self.create(restart=True)
        
    def restart(self):
        self.updateNode()
        result = None
#         reboot doesn't seem to work so commenting out
#         if self.node != None:
#             result = self.trycommand(self.myDriver.reboot_node, self.node)
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
            if self.ssh_error_counter == 1: 
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
    
    # code to run to initialize read/write disks, will copy disks contents to disk from some source
    def _initialize_disks(self):
        result = "\n".join([d.initialization_script() for d in self.read_write_disks])
        for i in range(min(self.numLocalSSD, len(self.localSSDInitSources))):
            source = self.localSSDInitSources[i]
            if source != "":
                result += "\n"+"gsutil rsync -r "+source+" /mnt/lssd-"+str(i)
        return result

    def _save_disk_content(self):
        # save disk content
        result="\n".join(map(lambda disk: disk.contentSave("/usr/local/bin/python2.7 "+self.rootdir+"DynamicDiskCloudSoftware/Worker/writeDiskContentFile.py"), self.read_write_disks))
        # save disk files to other location (e.g. cloud storage)
        result += "\n".join([d.shutdown_save_script() for d in self.read_write_disks])
        for i in range(min(self.numLocalSSD, len(self.localSSDDests))):
            dest = self.localSSDDests[i]
            if dest != "":
                result += "\n"+"gsutil rsync -r /mnt/lssd-"+str(i)+ " "+dest
        return result

    def _mount_local_ssd(self):
        return ["mkdir -p  /mnt/lssd-"+str(i)+ "\n /usr/share/google/safe_format_and_mount -m 'mkfs.ext4 -F' /dev/disk/by-id/scsi-"+str(i)+"Google_EphemeralDisk_local-ssd-"+str(i)+" /mnt/lssd-"+str(i) for i in range(self.numLocalSSD)]
    
    # code to mount disks
    def _mountDisksScript(self):
        read_only=map(lambda disk: disk.mount_script(False), self.read_disks)
        read_write=map(lambda disk: disk.mount_script(True), self.read_write_disks)
        local_ssd=self._mount_local_ssd()
        print self.rootdir
        read_write_disk_restore = map(lambda disk: disk.contentRestore("/usr/local/bin/python2.7 "+self.rootdir+"DynamicDiskCloudSoftware/Worker/restoreDiskContent.py"), self.read_write_disks)
        result= "\n".join(read_only+read_write+local_ssd+read_write_disk_restore)
        return result
    
    # code to unmount disks
    
    def _unmountDisksScript(self):
        read_only=map(lambda disk: disk.unmount_script(), self.read_disks)
        read_write=map(lambda disk: disk.unmount_script(), self.read_write_disks)
        result= "\n".join(read_only+read_write)
        return result
    
    def _setActiveGcloudAuthAccount(self):
        if self.myDriver.auth_account!=None:
            return "gcloud config set account "+self.myDriver.auth_account
        else: return ""
    
    # package script in python script shell
    # the StartupWrapper.py program executes the script, saves the output to google cloud storage and updates the project meta data on start and completion

    def packageScript(self):
        script = self._mountDisksScript()+"\n"+self._setActiveGcloudAuthAccount()+"\n"+self._initialize_disks()+"\n"+self.script+"\n"+self._save_disk_content()
        shutdownscript = self._unmountDisksScript()
        result = "\n#! /bin/bash"
        if self.activateStackdriver: result += "\nsudo bash stack-install.sh --api-key="+self.StackdriverAPIKey
#         result += "".join(map(lambda x: "\ngcutil cp gs://cmelton_wgs1/"+x+" /home/cmelton/GCE_Cluster/Worker/", ["InstanceData.py", "InstanceEngine.py", "Startup.py"]))
#         print result
        result += "\n/usr/local/bin/python2.7 "+self.rootdir+"DynamicDiskCloudSoftware/Worker/Startup.py --S \""+script.replace("\'", "'")+"\" --SD \""+shutdownscript.replace("\'", "'")+"\" --H "+self.rootdir+"StartupCommandHistoryv3.pickle --N "+self.name
        return(result)
    
    # create and run node on GCE

    def create(self, restart = False):
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
#             print self.packageScript()
            if not restart:
                if self.scriptAsParam:
                    self.node_params["ex_metadata"]["items"].append({"key":"startup-script", "value":self.packageScript()})
                else:
                    raise Exception("deploy with script from file or cloud storage not implemented yet")
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
                self.boot_disk.updateDisk()
                self.node=self.trycommand(self.myDriver.create_node, self.name, self.node_params["size"], self.node_params["image"], location=self.node_params["location"],
                                      ex_network=self.node_params["ex_network"], ex_tags=self.node_params["ex_tags"], ex_metadata=self.node_params["ex_metadata"], 
                                      ex_boot_disk=self.boot_disk.disk, serviceAccountScopes=["https://www.googleapis.com/auth/compute", "https://www.googleapis.com/auth/devstorage.read_write"], 
                                      additionalDisks=additionalDisks, preemptible=self.preemptible, numLocalSSD=self.numLocalSSD, log=self.log)
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
    
    #self.destroy(instances=None, destroydisks=False, force = False)
    
    def updateNode(self):
        self.node=self.trycommand(self.myDriver.ex_get_node, self.name)
        if self.node == None: self.destroyed=True
    
    def destroy(self, instances=None, destroydisks=True, force = False):
        self.updateNode()
        # detatch disks and destroy if not needed
        for disk in self.read_disks:
            if not force and self.node!=None: disk.detach(self)
            if destroydisks:
                disk.destroyifnotneeded(instances)
        for disk in self.read_write_disks:
            if not force and self.node!=None: disk.detach(self)
            if destroydisks: 
                disk.destroyifnotneeded(instances)
        # destroy node
        if self.node!=None and not self.destroyed:
            self.trycommand(self.myDriver.destroy_node, self.node)
            self.node=None
            self.printToLog("destroyed instance on GCE")
            # self.boot_disk.destroy() # boot disk seems to destroy itself so commenting this out
            self.destroyed=True
            self.created=False
        else:
            self.printToLog("mistakenly trying to destroy "+self.name+", destroyed "+str(self.destroyed)+" self.node "+str(self.node==None))
            self.destroyed=True
            self.created=False
        

    def trycommand(self, func, *args, **kwargs):
        tries = 0
        retries = 1
        while tries<retries:
            try:
                x = func(*args, **kwargs)
                return x
            except:
                e = sys.exc_info()[0]
                tries +=1
                time.sleep(10)
                self.printToLog(str(func) + " Error: "+str(e)+", "+str(e.__dict__)+ " try #"+str(tries)) 
        return None
                
                