from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import sys, time

'''
This file contains the model for disks.
'''

class Disk:
    def __init__(self, name, size, location, snapshot, myDriver, image, instanceNames, log, disk_type = 'pd-standard', init_source="", shutdown_dest=""):
        self.name=name
        self.size=size
        self.location=location
        self.snapshot=snapshot
        self.image=image
        self.myDriver=myDriver
        self.created=False
        self.destroyed=False
        self.disk=None
        self.mode="READ_WRITE"
        self.instanceNames=instanceNames
        self.log=log
        self.printToLog("initialized disk class")
        self.formatted=False
        self.disk_type=disk_type
        self.init_source = init_source
        self.shutdown_dest = shutdown_dest

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

    # this method returns a string that is a command to be run on the instance mounting this disk
    # thie command calls a program that removes content that should not be on the disk 
    # (i.e. content saved to disk if a prior instance was shutdown prior to completing)
    def contentRestore(self, restoreProgramPath):
        return restoreProgramPath+ " --P /mnt/"+self.name +" --F /mnt/"+self.name+"/"+"disk.content"

    # in concert with the above method this one calls a program that saves the directories and files stored on the disk
    # this creates a disk content file that the contentResetore program uses to know what the last saved state of the disk
    # was, these commands together allow the user to use preemptible VMs and as long as no files were deleted or altered, 
    # return the disk to the prior state and rerun the instance if it gets preempted
    def contentSave(self, saveProgramPath):
        return saveProgramPath+ " --P /mnt/"+self.name +" --F /mnt/"+self.name+"/"+"disk.content"

    # this method reteurns a command to initialize a disk from some source (i.e. another disk or from a storage bucket)
    def initialization_script(self):
        if self.init_source != "":
            return "gsutil rsync -r "+self.init_source+" /mnt/"+self.name
        return ""
    
    # this method returns a script to save disk contents to dest directory (i.e. another disk or a storage bucket)
    def shutdown_save_script(self):
        if self.shutdown_dest != "":
            return "gsutil rsync -r /mnt/"+self.name+" "+self.shutdown_dest
        return ""

    # this method returns a command for mounting this disk
    def mount_script(self, isWrite):
        result="mkdir -p /mnt/"+self.name
        if self.formatted:
            if isWrite:
                result+="\nmount /dev/disk/by-id/google-"+self.name+" /mnt/"+self.name+" -t ext4"
            else:
                result+="\nmount -o ro,noload /dev/disk/by-id/google-"+self.name+" /mnt/"+self.name+" -t ext4"
        else:
            result+="\n/usr/share/google/safe_format_and_mount -m 'mkfs.ext4 -F' /dev/disk/by-id/google-"+self.name+" /mnt/"+self.name
        self.formatted=True
        return result
    
    # this methods returns a command for unmounting this disk
    def unmount_script(self):
        result = "umount /mnt/"+self.name
        return result 
    
    # given a list of libcloud disks this method associates the libcloud disk with this disk class if
    # the name matches 
    def setDisk(self, disks):
        for disk in disks:
            if disk.name==self.name:
                self.disk=disk
                self.created=True
                self.formatted=True
    
    # this method returns a tab delimited data in a dictionary with information about this disk
    def tabDelimSummary(self):
        return {"header":"\t".join(["name", "size", "location", "snapshot", "image", 
                                    "myDriver", "created", "destroyed", "disk", "instanceNames", "log"]), 
                "values":"\t".join(map(lambda x: str(x), [self.name, self.size, self.location, self.snapshot, self.image, 
                          self.myDriver, self.created, self.destroyed, self.disk, self.instanceNames, self.log]))}

    # prints text data to a log file
    def printToLog(self, text):
        output=self.name+"\t"+text
        self.log.write(output)

    # this method returns tab delimited data about this disk as a string 
    def toString(self):
        tabDelim=self.tabDelimSummary()
        return("\n".join([tabDelim["header"],tabDelim["values"]]))

    # adds the names of the instances that this disk will be associated with
    def addInstance(self, instanceName):
        if instanceName not in self.instanceNames:
            self.instanceNames.append(instanceName)

    # this method creates the disk in the cloud
    def create(self):
        self.printToLog("trying to create disk... destroyed: "+str(self.destroyed)+" created: "+str(self.created)+" None: "+str(self.disk==None))
        if self.destroyed or not self.created:
            self.disk=self.trycommand(self.myDriver.create_volume, self.size, self.name, location=self.location, snapshot=self.snapshot, image=self.image, ex_disk_type=self.disk_type)
            self.created=True
            self.destroyed=False
            self.printToLog("created disk on GCE")
        else:
            self.printToLog("did not create disk on GCE")
    
    # this command pings the GCE API and updates this disk with the libcloud disk if it exists
    def updateDisk(self):
        self.printToLog("updating disk "+self.name)
        self.disk=self.trycommand(self.myDriver.ex_get_volume, self.name)
        if self.disk == None: self.destroyed=True
    
    # this method destroys this disk
    def destroy(self):
        self.updateDisk()
        if self.created and not self.destroyed:
#             if 'download' not in self.name: 
            self.trycommand(self.myDriver.destroy_volume,self.disk)
            self.printToLog("destroyed disk on GCE")
        self.destroyed=True
        self.disk = None

    # this method destroys this disk if no other instance will be using this disk
    def destroyifnotneeded(self, instances):
        if instances!=None:
            for instance_name in instances:
                inst = instances[instance_name]
                disk_names=map(lambda x: x.name, inst.read_disks+inst.read_write_disks)
                if self.name in disk_names:
                    if instances[instance_name].status!="complete":
                        return
            print "should destroy "+self.name
            self.destroy()

    # this method attaches this disk to an instance, this is necessar for GCE instance to be able to mount this disk
    def attach(self, instance):
        self.printToLog("attached disk to "+instance.name+" on GCE")
        if instance.node!=None:
            self.trycommand(self.disk.attach, instance.node)
    
    # this method detaches the disk from the instance
    def detach(self, inst):
        if self.created and not self.destroyed:
            self.printToLog("trying to detach disk on GCE from "+inst.name)
            self.trycommand(self.myDriver.detach_volume, self.disk, inst.node)
            self.printToLog("detached disk on GCE from "+inst.name)

    # this meethod tries to execute a command a certain number of times before returning None
    def trycommand(self, func, *args, **kwargs):
        retries = 1
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