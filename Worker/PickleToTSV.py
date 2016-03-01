'''
Created on Oct 8, 2015

@author: cmelton

When run as main this program parses either a single instance data pickle file or a folder of such files and outputs
one or more tsv files with performance over time.

'''


from InstanceData import *
import pickle
from optparse import OptionParser
import psutil, os


# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--I", dest = "inputFile", help = "",
                      metavar = "FILE", type = "string", default = "/Users/cmelton/Documents/AptanaStudio3WorkspaceNew/DynamicDiskCloudSoftware/TestResults/PickleFiles/std-norm2-node-1-cancer-pup.history.pickle")
    parser.add_option("--O", dest = "outputFile", help = "",
                      metavar = "FILE", type = "string", default = "/Users/cmelton/Documents/AptanaStudio3WorkspaceNew/DynamicDiskCloudSoftware/TestResults/PerformanceFiles/std-norm2-node-1-cancer-pup.perf.tsv")
    parser.add_option("--ID", dest = "inputFileDir", metavar = "FILE", default = "/Users/cmelton/Documents/AptanaStudio3WorkspaceNew/DynamicDiskCloudSoftware/TestResults/PickleFiles/NewNaming/")
    parser.add_option("--OD", dest = "outputFileDir", metavar = "FILE", default = "/Users/cmelton/Documents/AptanaStudio3WorkspaceNew/DynamicDiskCloudSoftware/TestResults/PerformanceFiles/NewNaming/")
    (options, args) = parser.parse_args()
    return options

def getCommandPerformanceData(command, perfdata):
    pd = PerformanceData()
    if command.start_time!="NA" and command.end_time!="NA":
        pd.performanceLog = [p for p in perfdata.performanceLog if p.time > command.start_time and p.time < command.end_time]
    return pd

def getTSVFormattedData(PD, identifier, command_abbr, command):
    command = command.replace("\t", "_").replace("\n", "_").replace(" ", "_") 
    command_abbr = command_abbr.replace("\t", "_").replace("\n", "_").replace(" ", "_") 
    previous=None
    result = []
    for log in PD.performanceLog: 
        if previous==None:
            writespeed=0
            readspeed=0
        else:
            writespeed=(log.write_bytes-previous.write_bytes)/1000000/((log.time-previous.time).total_seconds())
            readspeed=(log.read_bytes-previous.read_bytes)/1000000/((log.time-previous.time).total_seconds())
        result.append("\t".join(map(str, [identifier]+log.tsv()+[writespeed, readspeed, command_abbr, command])))
        previous=log
    return result

def getSummary(InstanceData, identifier):
    commands = InstanceData['CommandData'].commands
    perfData = InstanceData['PerformanceData']
    commandPerformanceData = [(getCommandPerformanceData(command, perfData), command) for command in commands] 
    tsvHeader = ["identifier"] + ["time", "cpu", "memory", "read_count", "write_count", "read_bytes", "write_bytes", "read_time", "write_time", "write_speed", "read_speed"]+["command_abbreviation", "command"]
    tsvHeader = "\t".join(tsvHeader)
    tsvData = ["\n".join(getTSVFormattedData(PD, identifier, command.command[:min(300, len(command.command))], command.command)) for PD, command in commandPerformanceData]
    tsvData = [t for t in tsvData if t != ""]
    return "\n".join([tsvHeader]+tsvData)

def printSummaryToFile(filename, InstanceData, identifier):
    toprint = getSummary(InstanceData, identifier)
    f = open(filename, 'w')
    f.write(toprint)
    f.close()

if __name__ == '__main__':
    options = getOptions()
    if options.inputFileDir != "" and options.outputFileDir !="" and os.path.exists(options.inputFileDir) and os.path.exists(options.outputFileDir):
        files = os.listdir(options.inputFileDir)
        for fname in files:
            print fname
            if ".pickle" in fname:
                f=open(os.path.join(options.inputFileDir, fname), 'r')
                ID = pickle.load(f)
                f.close()
                ID['PerformanceData'].writeSummary(os.path.join(options.outputFileDir, fname[:-7]+".tsv"), byprocess=True)

    else:
        f=open(options.inputFile, 'r')
        ID = pickle.load(f)
        f.close()
        ID['PerformanceData'].writeSummary(options.outputFile)