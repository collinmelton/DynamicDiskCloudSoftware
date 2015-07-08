import thread, datetime

# This function allows multiple threads to write to the same logfile, it prevents
# multiple threads from writing at the same time by adding a lock
class LogFile():
    '''
    This class logs data.
    '''
    def __init__(self, fileName):
        self.fileName=fileName
        self.lock=thread.allocate_lock()
        try:
            f = open(self.fileName, 'w')
            f.write("logfile start")
            f.close()
        except:
            print "something is wrong with log file"
        
    def __str__(self):
        return self.fileName

    # write with new line and date-time
    def write(self, textToWrite):
        self.lock.acquire()
        f = open(self.fileName, 'a')
        # write time then add text to write
        f.write("\n"+datetime.datetime.now().strftime("%Y-%m-%d %H:%M")+"\t")
        f.write(str(textToWrite))
#         print textToWrite
        if f: f.close()
        self.lock.release()
    
    # write without date or newlines etc
    def writeRaw(self, textToWrite):
        self.lock.acquire()
        try:
            f = open(self.fileName, 'a')
            # write time then add text to write
            f.write(textToWrite)
            print textToWrite
            if f: f.close()
        except:
            print "something is wrong with raw log file writing"
        self.lock.release()