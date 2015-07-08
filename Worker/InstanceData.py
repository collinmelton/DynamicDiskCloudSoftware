
import datetime, psutil, os, subprocess, thread, pickle

# return (now, {"cpu":psutil.cpu_percent(), "memory":psutil.virtual_memory().percent})
# current_time.isoformat()

# certain text output for GATK can indicate that the command didn't actually fail even with non zero exit status 
NOT_ACTUALLY_FAILED_LIST=["org.broadinstitute.sting.gatk.CommandLineExecutable.generateGATKRunReport", "org.broadinstitute.gatk.engine.CommandLineExecutable.generateGATKRunReport"]

# get the current time
def whatTimeIsIt():
    return datetime.datetime.now()
   
# class to store instance performance data at a particular time
class Performance(object):
    '''
    This class represents a class that sores performance data for a specific moment in time.
    '''
    def __init__(self, time, cpu, memory, read_count=None, write_count=None, read_bytes=None, 
                 write_bytes=None, read_time=None, write_time=None):
        self.time=time
        self.cpu=cpu
        self.memory=memory
        self.read_count=read_count
        self.write_count=write_count
        self.read_bytes=read_bytes
        self.write_bytes=write_bytes
        self.read_time=read_time
        self.write_time=write_time
        
    def header(self):
        if self.read_count!=None:
            return ["time", "cpu", "memory", "read_count", "write_count", "read_bytes", "write_bytes", "read_time", "write_time"]
        return ["time", "cpu", "memory"]
    
    def tsv(self):
        if self.read_count!=None:
            return map(str, [self.time, self.cpu, self.memory, self.read_count, self.write_count, self.read_bytes, self.write_bytes, self.read_time, self.write_time])
        return map(str, [self.time, self.cpu, self.memory])

# class to store instance performance data for all times
class PerformanceData(object):
    '''
    This class represents a class that stores system performance data.
    '''
    def __init__(self):
        self.performanceLog=[]
    
    def to_tsv(self, identifier, include_header):
        header=["identifier"]+self.performanceLog[0].header()
        result= map(lambda p: [identifier]+p.tsv(), self.performanceLog)
        if include_header: return [header]+result
        return result
        
    def update(self):
        now = whatTimeIsIt()
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        # read_count: number of reads
        # write_count: number of writes
        # read_bytes: number of bytes read
        # write_bytes: number of bytes written
        # read_time: time spent reading from disk (in milliseconds)
        # write_time: time spent writing to disk (in milliseconds)
        iodata=psutil.disk_io_counters()
        read_count=iodata.__dict__["read_count"]
        write_count=iodata.__dict__["write_count"]
        read_bytes=iodata.__dict__["read_bytes"]
        write_bytes=iodata.__dict__["write_bytes"]
        read_time=iodata.__dict__["read_time"]
        write_time=iodata.__dict__["write_time"]
        self.performanceLog.append(Performance(now, cpu, memory, read_count, write_count, read_bytes, write_bytes, read_time, write_time))
            
    def maxCPU(self):
        maxval=0
        for p in self.performanceLog:
            maxval=max(maxval, p.cpu)
        return maxval

    def maxMem(self):
        maxval=0
        for p in self.performanceLog:
            maxval=max(maxval, p.memory)
        return maxval
    
    def summary(self):
        return "max_cpu: "+str(self.maxCPU())+", max_mem: "+str(self.maxMem())
    
    def writeSummary(self, filename):
        f=open(filename, 'w')
        previous=None
        for log in self.performanceLog: 
            if previous==None:
                header=log.header()+["write_speed", "read_speed"]
                f.write("\t".join(header))
                writespeed=0
                readspeed=0
            else:
                writespeed=(log.write_bytes-previous.write_bytes)/1000000/((log.time-previous.time).total_seconds())
                readspeed=(log.read_bytes-previous.read_bytes)/1000000/((log.time-previous.time).total_seconds())
            f.write("\n"+"\t".join(log.tsv()+map(str, [writespeed, readspeed])))
            previous=log
        f.close()

# class to store individual commands and run them
class Command():
    '''
    This class represents a class that stores data for a single command.
    '''
    def __init__(self, command):
        self.start_time="NA"
        self.end_time="NA"
        self.command=command
        self.finished=False
        self.result="not run yet"
        self.failed=False
    
    def getStatus(self):
        if self.finished: 
            if self.failed: return "failed"
            else: return "complete"
        else: return "not finished"  
    
    def header(self):
        return ["start_time", "end_time", "command", "result", "finished", "failed"]
    
    def toGvisTable(self):
        description = {"Start": ("string", "Start Time"),
                       "Stop": ("string", "End Time"),
                       "Finished": ("boolean", "Finished"),
                       "Failed": ("boolean", "Failed")
#                        ,
#                        "Command": ("string", "Command"),
#                        "Result": ("string", "Result")
                       }
        result= {"Start": str(self.start_time),
                 "Stop": str(self.end_time),
                 "Finished": self.finished,
                 "Failed": self.failed
#                  ,
#                  "Command": self.command,
#                  "Result": self.result
                 }
        return (description, result)
    
    def tsv(self):
        return map(str, [self.start_time, self.end_time, self.command, self.result, self.finished, self.failed])
    
    def setlock(self, lock):
        self.lock=lock
    
    def __str__(self):
        return "\n".join(["=========================",
                          "command:\t"+self.command,
                          "result:\t"+self.result])
    
    def __repr__(self):
        return "\n".join(["=========================",
                          "command:\t"+self.command,
                          "result:\t"+self.result])
    
    # run the command if not already run and finished
    def run(self):
        print "command:", self.command
        if not self.finished:
            self.lock.acquire()
            self.start_time=whatTimeIsIt()
            self.lock.release()
            try: result=subprocess.check_output(self.command,shell=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                result = "\n".join(map(str, [e.cmd, e.returncode, e.output]))
                print "failed"
                notfailed=False
                self.failed = True
                for item in NOT_ACTUALLY_FAILED_LIST:
                    if item in result or item in e.output:
                        notfailed=True
                if notfailed:
                    self.failed=False
            self.lock.acquire()
            self.result=result
            self.end_time=whatTimeIsIt()
            self.lock.release()
        print "result:", self.result
        self.finished=True
        return self.failed

# splits text on multiple values in order
def splitMultiple(text, splitChars):
    vals=text.split(splitChars[0])
    for splitChar in splitChars[1:]:
        newvals=map(lambda x: x.split(splitChar), vals)
        vals=reduce(lambda x,y: x+y, newvals)
    return vals

# class to store instance performance data for all times
class CommandData(object):
    '''
    This class represents a class that stores data for multiple commands.
    '''
    def __init__(self, inputScriptFile):
        self.inputScriptFile=inputScriptFile
        self.commands=self.parseCommands()
        self.currentCommand=0
        self.status="started"
    
    def to_tsv(self, identifier, include_header):
        header=["identifier"]+self.commands[0].header()
        result= [header]+map(lambda c: [identifier]+c.tsv(), self.commands)
        if include_header: return [header]+result
        return result
    
    def setlock(self, lock):
        self.lock=lock
        for c in self.commands:
            c.setlock(self.lock)
    
    # returns next command to run
    def next(self):
        self.lock.acquire()
        if (self.currentCommand+1)>len(self.commands):
            self.status="complete"
            self.lock.release()
            return None
        next= self.commands[self.currentCommand]
        self.currentCommand+=1
        self.lock.release()
        return next
        
    # parses and loads commands from script file or from command history file if restart        
    def parseCommands(self):
        commands=[]
        lines=splitMultiple(self.inputScriptFile.replace("\\'", "'"), ["\\\n", "\\n", "\n"])
        for line in lines:
            print line
            if line!="": commands.append(Command(line))
        return commands
    
    def summary(self):
        return "\n".join(map(str, self.commands))

# class to store all data concerning a particular on on a particular instance
class InstanceData(object):
    '''
    This class represents a class that stores data about the commands and performances being run on
    a particular instance.
    '''
    def __init__(self, name, inputScriptFile, InstanceHistoryFile):
        self.lock=thread.allocate_lock()
        self.name=name
        self.InstanceHistoryFile=InstanceHistoryFile
        if os.path.exists(self.InstanceHistoryFile):
            f=open(self.InstanceHistoryFile, 'r')
            savedData=pickle.load(f)
            f.close()
            self.run_performance_data=savedData["PerformanceData"]
            self.command_data=savedData["CommandData"]
        else:
            self.run_performance_data=PerformanceData()
            self.command_data=CommandData(inputScriptFile)
        self.command_data.setlock(self.lock)
        
    def updatePerformance(self):
        self.lock.acquire()
        self.run_performance_data.update()
        self.lock.release()
    
    def save(self):
        self.lock.acquire()
        self.command_data.setlock(None)
        f=open(self.InstanceHistoryFile, 'w')
        pickle.dump({"PerformanceData":self.run_performance_data,
                     "CommandData":self.command_data}, f)
        f.close()
        self.command_data.setlock(self.lock)
        self.lock.release()
        
    def nextCommand(self):
        return self.command_data.next()
        
    def summary(self):
        if self.command_data.status=="Finished": result="all commands completed"
        else: result=str(self.command_data.currentCommand)+"/"+str(len(self.command_data.commands))+" run"
        result+="\n"+self.run_performance_data.summary()
        result+="\n"+self.command_data.summary()
        return result
    
    def writeSummaryToFile(self, filename):
        self.run_performance_data.writeSummary(filename)
    
    def finished(self):
        if self.status()=="complete" or self.status()=="failed": return True
        return False
    
    def failed(self):
        self.command_data.status="failed"
        self.save()

    
    def getStatus(self):
        if self.finished: 
            if self.failed: return "failed"
            else: return "complete"
        else: return "not finished"  
    
    def update_status(self):
#         statuses = [c.getStatus() for c in self.command_data.commands]
#         if "failed" in statuses: return "failed"
#         if "not finished" in statuses: return "started"
#         return "complete"
        last_command=self.command_data.commands[self.command_data.currentCommand-1]
        if last_command.failed: self.command_data.status="failed"
        if last_command.finished and not last_command.failed and self.command_data.currentCommand>=len(self.command_data.commands):
            self.command_data.status="complete"
    
    def commands_to_table(self, include_header):
        return self.command_data.to_tsv(self.name, include_header)
    
    def performance_to_table(self, include_header):
        return self.run_performance_data.to_tsv(self.name, include_header)
    
    def status(self):
        self.update_status()
        return self.command_data.status