'''
Created on Jul 25, 2014

@author: cmelton
'''

from optparse import OptionParser
import InstanceEngine

# this functions gets the command line options for running the program
def getOptions():
    parser = OptionParser()
    parser.add_option("--S", dest = "ScriptFile", help = "this should be a text form of a startup script",
                      metavar = "STRING", type = "string", default = "echo hello")
    parser.add_option("--H", dest = "HistoryFile", help = "sets location of commands history file",
                      metavar = "STRING", type = "string", default = "/home/cmelton/StartupCommandHistory.pickle")
    parser.add_option("--N", dest = "name", help = "sets name of instance",
                      metavar = "STRING", type = "string")
    parser.add_option("--SD", dest = "onShutdown", help = "to run on failure",
                      metavar = "STRING", type = "string")
    parser.add_option("--PF", dest = "performanceDataFile", help = "file to write performance data",
                      metavar = "STRING", type = "string", default = "./perfData.tsv")
    (options, args) = parser.parse_args()
    return options

if __name__ == '__main__':
    options=getOptions()
    engine=InstanceEngine.InstanceEngine(options.ScriptFile, options.onShutdown, options.HistoryFile, options.name,
                                         performanceDataFile=options.performanceDataFile)
    engine.run()