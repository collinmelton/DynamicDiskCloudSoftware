'''
Created on Jul 31, 2014

@author: cmelton

some code to make html pages from instance performance and status data, haven't used in a while and it doesn't look 
like I documented this well so use at your own risk!

'''

import os, subprocess, time, pickle, sys, csv, gviz_api, pickle, datetime
from InstanceData import *

from optparse import OptionParser


class InstancePage(object):
    
    def __init__(self, instanceData, name, outputDirectory, instanceTemplate):
        self.instanceData=instanceData
        self.name=name.split("/")[-1].split("node", 1)[1].replace(".history.pickle", "").replace("-", "")
        self.patient_id=name.split("/")[-1].split("-node")[0][2:]
        self.html_filename=self.name+".html"
        self.html_instance_list_filename=self.name+"_instance.html"
        self.full_filename=os.path.join(outputDirectory,"patients/"+self.patient_id+"/"+self.html_filename)
        self.instanceTemplate=instanceTemplate
        self.completed = self.instanceData.command_data.currentCommand 
        self.remaining = len(self.instanceData.command_data.commands)-self.instanceData.command_data.currentCommand
        self.status = self.instanceData.command_data.status
        self.maxCPU = self.instanceData.run_performance_data.maxCPU()
        self.medCPU = self.instanceData.run_performance_data.medCPU()
        self.maxMem = self.instanceData.run_performance_data.maxMem()
        self.medMem = self.instanceData.run_performance_data.medMem()
        self.totaltime = self.instanceData.run_performance_data.totalTime()
        self.numcommands = len(self.instanceData.command_data.commands)
        self.currentcommand = self.instanceData.command_data.currentCommand
    
    def generateCommandTable(self):
        description = self.instanceData.command_data.commands[0].toGvisTable()[0]
        data = map(lambda command: command.toGvisTable()[1], self.instanceData.command_data.commands)
        data_table = gviz_api.DataTable(description)
        data_table.LoadData(data)
        
        # Creating a JavaScript code string
        result = data_table.ToJSCode("jscode_data", 
                                     columns_order=tuple(description.keys()), 
                                     order_by="Finished")
        return result
    
    def generateHTML(self):
        jscodeCommands = self.generateCommandTable()
        name=self.name.strip(".history")+" "+"Status Report"
        self.instanceData=None
        return self.instanceTemplate % vars()
    
    def MainTableRow(self):
        result= {"Patient ID": self.patient_id,
                "Instance Name": "<a href=\""+self.patient_id+"/"+self.html_filename+"\">"+self.name.replace(".history.pickle","")+"</a>", 
                "Jobs Completed": self.completed, 
                "Jobs Remaining": self.remaining,
                "Status": self.status,
                "CPU (Max)": self.maxCPU,
                "CPU (Med)": self.medCPU,
                "Mem (Max)": self.maxMem,
                "Mem (Med)": self.medMem, 
                "Duration": self.totaltime}
        return result

class JobDataToHTML(object):
    '''
    This class contains functionality to create a nice html presentation of gce job data.
    '''


    def __init__(self, mainPageTemplateFile="./TestData/template.html", instanceTemplateFile="./TestData/instance_template.html",
                 outputDirectory="./TestData/test", pickleDirectory="./TestData/", historyDirectory="./TestData/"):
        '''
        Constructor
        '''
        self.outputDirectory=outputDirectory
        self.pickleDirectory=pickleDirectory
        self.historyDirectory=historyDirectory
        f=open(mainPageTemplateFile, "r")
        self.mainPageTemplate=f.read()
        f.close()
        f=open(instanceTemplateFile, "r")
        self.instanceTemplate=f.read()
        f.close()
    
    # prints text data to a file
    def printFile(self, text, filename):
        directory = os.path.dirname(os.path.realpath(filename))
        if not os.path.exists(directory): os.makedirs(directory)
#         print filename
        f=open(filename, 'w')
        f.write(text)
        f.close()
    
    def PatientTableRow(self, instancePages): 
        patientIDs=map(lambda x: x.patient_id, instancePages.values())
        completion_fractions=map(lambda x: float(x.currentcommand)/x.numcommands, instancePages.values())
        statuses=map(lambda x: x.status, instancePages.values())
#         print statuses
        if "failed" in statuses: status="failed"
        elif "started" in statuses: status="started"
        elif "not started" in statuses: status = "not started"
        else: status="complete"
        names=map(lambda x: x.name, instancePages.values())
        result= {"Patient ID": "<a href=\"patients/"+patientIDs[0]+".html"+"\">"+patientIDs[0]+"</a>",
                "Instances Completed": sum([1 for x in instancePages.values() if x.status=="complete"]), 
                "Instances Remaining": sum([1 for x in instancePages.values() if x.status!="complete"]), 
                "Running Instances": ", ".join([names[i].replace(".history.pickle","") for i in range(len(statuses)) if statuses[i]=="started"]),
                "Failed Instances": ", ".join([names[i].replace(".history.pickle","") for i in range(len(statuses)) if statuses[i]=="failed"]),
                "Status": status
                }
        return result
    
    def PatientPage(self, instancePagesByPatient):
        description = {"Patient ID": ("string", "Patient"),
                       "Instances Completed": ("number", "Completed"),
                       "Instances Remaining": ("number", "Remaining"),
                       "Running Instances": ("string", "Running"),
                       "Failed Instances": ("string", "Failed"),
                       "Status": ("string", "Status") 
                       }
        data = map(lambda patient: self.PatientTableRow(instancePagesByPatient[patient]), instancePagesByPatient.keys())
        
        # Loading it into gviz_api.DataTable
        data_table = gviz_api.DataTable(description)
        data_table.LoadData(data)
        
        # Creating a JavaScript code string
        jscode = data_table.ToJSCode("jscode_data", 
                                     columns_order=("Patient ID", "Instances Completed", "Instances Remaining", "Running Instances", "Failed Instances", "Status"), 
                                     order_by="Status")
        name="Patient Report"
        return self.mainPageTemplate % vars()
    
    
    
    # returns a text for the main page
    def MainPage(self, InstancePages):
        description = {"Patient ID": ("string", "Patient"),
                       "Instance Name": ("string", "Name"),
                       "Jobs Completed": ("number", "Completed"),
                       "Jobs Remaining": ("number", "Remaining"),
                       "Status": ("string", "Status"), 
                       "CPU (Max)": ("number", "Max CPU"),
                       "CPU (Med)": ("number", "Median CPU"),
                       "Mem (Max)": ("number", "Max Memory"),
                       "Mem (Med)": ("number", "Median Memory"), 
                       "Duration": ("number", "Duration")}
        data = map(lambda instPage: instPage.MainTableRow(), InstancePages)
        
        # Loading it into gviz_api.DataTable
        data_table = gviz_api.DataTable(description)
        data_table.LoadData(data)
        
        # Creating a JavaScript code string
        jscode = data_table.ToJSCode("jscode_data", 
                                     columns_order=("Patient ID", "Instance Name", "Status", "Jobs Completed", "Jobs Remaining", "CPU (Max)", "CPU (Med)", "Mem (Max)", "Mem (Med)", "Duration"), 
                                     order_by="Status")
        name="Instance Status Report"
        return self.mainPageTemplate % vars()
        
    # returns a dict of instance data after extracting instance data from all pickle files in a directory
    def getInstanceData(self, pickleDirectory):
        result={}
        for p in os.listdir(pickleDirectory):
            if ".pickle" in p: 
                pnopickle = p.replace(".pickle", "")
                result[pnopickle] = {'data':InstanceData(pnopickle, "None", os.path.join(pickleDirectory,p))}
                result[pnopickle]["data"].update_status()
        self.instanceDataDict=result
#         print result.keys()
        return self.instanceDataDict.keys()
    
    def updateInstancePages(self, toupdate, outputDirectory=""):
        j = 0
        for i in toupdate:
            j+=1
            print j,
            filesize = os.path.getsize(i)
            dontskip = True
            if i not in self.filesizes:
                self.filesizes[i]=filesize
            else:
                if self.filesizes[i]==filesize: dontskip=False
            if dontskip:
#                 print j
                pnopickle = i.replace(".pickle", "")
                try:
#                     print i
                    data = InstanceData(pnopickle, "None", i)
                    if data.status()=="complete": self.finished.add(i)
                    page = InstancePage(data, i, outputDirectory, self.instanceTemplate)
                    if page.patient_id not in self.instancePagesByPatient:
                        self.instancePagesByPatient[page.patient_id] = {}
                    self.instancePagesByPatient[page.patient_id][page.name] = page
                    self.patients.add(page.patient_id)
                    self.printFile(page.generateHTML(), page.full_filename)
                except:
                    print "possible pickle error:", i, 
        self.printFile(self.PatientPage(self.instancePagesByPatient), os.path.join(outputDirectory, "index.html"))
        for patient in self.patients:
#             print outputDirectory
#             print os.path.join(outputDirectory, patient+".html")
#             print patient
            self.printFile(self.MainPage(self.instancePagesByPatient[patient].values()), os.path.join(outputDirectory, "patients/"+patient+".html"))
                
    def updatePages(self):
        self.GenerateResultsWebPage()
    
    def loadHistory(self, obj, path):
        if os.path.exists(path):
            f=open(path)
            obj = pickle.load(f)
            f.close()
        return obj
    
    def saveHistory(self, obj, path):
        f=open(path, "w")
        obj = pickle.dump(obj, f)
        f.close()
    
    def start(self):
        historyPath = self.historyDirectory
        self.finished = self.loadHistory(set(), os.path.join(historyPath, "finished.hist.pickle"))
        self.patients = self.loadHistory(set(), os.path.join(historyPath, "patients.hist.pickle"))
        self.filesizes = self.loadHistory({}, os.path.join(historyPath, "filesizes.hist.pickle"))
        self.instancePagesByPatient=self.loadHistory({}, os.path.join(historyPath, "instancePagesByPatient.hist.pickle"))
        self.GenerateResultsWebPage()
    
    def save(self):
        historyPath = self.historyDirectory
        self.saveHistory(self.finished, os.path.join(historyPath, "finished.hist.pickle"))
        self.saveHistory(self.patients, os.path.join(historyPath, "patients.hist.pickle"))
        self.saveHistory(self.filesizes, os.path.join(historyPath, "filesizes.hist.pickle"))
        self.saveHistory(self.instancePagesByPatient, os.path.join(historyPath, "instancePagesByPatient.hist.pickle"))
    
    # generates a series of html files with instance data
    def GenerateResultsWebPage(self):
        outputDirectory=self.outputDirectory
        pickleDirectory=self.pickleDirectory
        if "|" in pickleDirectory: 
            pds = pickleDirectory.split("|")
            toupdate=[]
            for pd in pds:
                toupdate+=[os.path.join(pd, f) for f in os.listdir(pd) if f[-7:]==".pickle" and f not in self.finished and ".history.pickle" in f]
        else:
            pd = pickleDirectory
            toupdate=[os.path.join(pd, f) for f in os.listdir(pd) if f[-7:]==".pickle" and f not in self.finished and ".history.pickle" in f]
#         toupdate = list(set(toupdate)-self.finished)
        print "# to update", len(toupdate)
        self.updateInstancePages(toupdate, outputDirectory=outputDirectory)
     
    # prints instance data to csv format
    def printInstanceDataToCSV(self, pickleDirectory, filenamebase):
        perf_csvfile = open("performance_"+filenamebase+".csv", 'wb')
        perf_datawriter = csv.writer(perf_csvfile)
        com_csvfile = open("commands_"+filenamebase+".csv", 'wb')
        com_datawriter = csv.writer(com_csvfile)
        instanceDataDict=self.getInstanceData(pickleDirectory)
        first=True
        for i_name in instanceDataDict:
            i=instanceDataDict[i_name]
            lines= i.performance_to_table(first)
            for line in lines: perf_datawriter.writerow(line)
            lines= i.commands_to_table(first)
            for line in lines: com_datawriter.writerow(line)
            first=False
        perf_csvfile.close()
        com_csvfile.close()

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()  
    parser.add_option("--MT", dest = "mainPageTemplateFile", help = "",
                      metavar = "FILE", type = "string", default = "./TestData/template.html")
    parser.add_option("--IT", dest = "instanceTemplateFile", help = "",
                      metavar = "FILE", type = "string", default = "./TestData/instance_template.html")
    parser.add_option("--P", dest = "pickleDirectory", help ="", 
                      metavar = "FILE", default = "./TestData/", type = "string")
    parser.add_option("--O", dest = "outputDirectory", help = "", 
                      metavar = "STRING", default = "./TestData/", type = "string")
    parser.add_option("--H", dest = "historyDirectory", help = "", 
                      metavar = "STRING", default = "./TestData/", type = "string")
    (options, args) = parser.parse_args()
    return options
      

if __name__ == '__main__':
    options=getOptions()
    j=JobDataToHTML(mainPageTemplateFile=options.mainPageTemplateFile, 
                             instanceTemplateFile=options.instanceTemplateFile,
                             outputDirectory=options.outputDirectory, 
                             pickleDirectory=options.pickleDirectory,
                             historyDirectory=options.historyDirectory)
    print options.mainPageTemplateFile, options.instanceTemplateFile, options.outputDirectory, options.pickleDirectory
    j.start()
    while True:
        j.updatePages()
        j.save()
        time.sleep(40)