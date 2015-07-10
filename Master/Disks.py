from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import sys, time


class Disk:
    def __init__(self, name, size, location, snapshot, myDriver, image, instanceNames, log):
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

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

    def mount_script(self, isWrite):
        result="sudo mkdir -p /mnt/"+self.name
        if self.formatted:
            if isWrite:
                result+="\nsudo mount /dev/disk/by-id/google-"+self.name+" /mnt/"+self.name+" -t ext4"
            else:
                result+="\nsudo mount -o ro,noload /dev/disk/by-id/google-"+self.name+" /mnt/"+self.name+" -t ext4"
        else:
            result+="\nsudo /usr/share/google/safe_format_and_mount -m 'mkfs.ext4 -F' /dev/disk/by-id/google-"+self.name+" /mnt/"+self.name
#         if isWrite:
#             result+="\nchmod a+w /mnt/"+self.name
#         else:
#             result+="\nchmod a+r /mnt/"+self.name
        self.formatted=True
        return result
    
    def unmount_script(self):
        result = "umount /mnt/"+self.name
        return result 
    
    def setDisk(self, disks):
        for disk in disks:
            if disk.name==self.name:
                self.disk=disk
                self.created=True
                self.formatted=True
        

    def tabDelimSummary(self):
        return {"header":"\t".join(["name", "size", "location", "snapshot", "image", 
                                    "myDriver", "created", "destroyed", "disk", "instanceNames", "log"]), 
                "values":"\t".join(map(lambda x: str(x), [self.name, self.size, self.location, self.snapshot, self.image, 
                          self.myDriver, self.created, self.destroyed, self.disk, self.instanceNames, self.log]))}

    def printToLog(self, text):
        output=self.name+"\t"+text
        self.log.write(output)

    def toString(self):
        tabDelim=self.tabDelimSummary()
        return("\n".join([tabDelim["header"],tabDelim["values"]]))
#         return("\n".join(map(lambda x: "\t"+str(x), [self.name, self.size, self.location, self.snapshot, self.image, 
#                           self.myDriver, self.created, self.destroyed, self.disk, self.instanceNames, self.log])))

    def addInstance(self, instanceName):
        if instanceName not in self.instanceNames:
            self.instanceNames.append(instanceName)

    def create(self):
        self.printToLog("created disk on GCE")
        if self.destroyed or not self.created:
            self.disk=self.trycommand(self.myDriver.create_volume, self.size, self.name, location=self.location, snapshot=self.snapshot, image=self.image)
            self.created=True
            self.destroyed=False
    
    def destroy(self):
        if self.created and not self.destroyed:
#             if 'download' not in self.name: 
            self.trycommand(self.myDriver.destroy_volume,self.disk)
            self.printToLog("destroyed disk on GCE")
        self.destroyed=True
        self.disk = None

    def destroyifnotneeded(self, instances):
        if instances!=None:
            # for each instance look to see if the disk is needed, if it is needed and the instance is not complete don't destroy (ie return)
#             disks_current_insts=[]
            for instance_name in instances:
                inst = instances[instance_name]
                disk_names=map(lambda x: x.name, inst.read_disks+inst.read_write_disks)
                if self.name in disk_names:
#                     print "for destroy if not needed, checking status of: "+instance_name+" "+inst.status
#                     if not inst.destroyed: 
#                         disks_current_insts.append(inst)
                    if instances[instance_name].status!="complete":
                        return
            print "should destroy "+self.name
#             for i in disks_current_insts: self.detach(i)
            self.destroy()

    def attach(self, instance):
        self.printToLog("attached disk to "+instance.name+" on GCE")
        if instance.node!=None:
            self.trycommand(self.disk.attach, instance.node)
    
    def detach(self, inst):
        if self.created and not self.destroyed:
            self.printToLog("trying to detach disk on GCE from "+inst.name)
            self.trycommand(self.myDriver.detach_volume, self.disk, inst.node)
            self.printToLog("detached disk on GCE from "+inst.name)

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
                self.printToLog(str(func) + " Error: "+str(e)+ " try #"+str(tries)) 
        return None