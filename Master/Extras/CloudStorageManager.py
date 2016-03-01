'''
Created on Jul 25, 2014

@author: cmelton
'''
import httplib2, subprocess

class CloudStorageManager(object):
    '''
    The class sends files to cloud storage.
    '''


    def __init__(self, cloud_type):
        '''
        Constructor
        '''
        self.cloud_type=cloud_type

    # gets instance attribute from metadata server
    def getInstanceAttribute(self, attribute):
        http = httplib2.Http()
        attributesUrl = self.metadataurl + 'instance/'+attribute
        resp,content = http.request(uri=attributesUrl, method='GET', body='', headers={'X-Google-Metadata-Request': 'True'})
        return content
 
    # gets instance name from metadata server
    def getInstanceName(self):
        content=self.getInstanceAttribute("hostname")
        return content.split(".")[0]
 
    # getes instance id from metadata server
    def getInstanceID(self):
        return self.getInstanceAttribute("id")
     
    # sends text data to cloud storage
    def sendOutputToCloudStorage(self, output, filename=""):
        if filename=="":
            instanceName=self.getInstanceName()
            instanceID=self.getInstanceID()
            filename=instanceName+"_"+instanceID+".output"
        f=open(filename, "w")
        f.write(output)
        f.close()
        command="gsutil cp "+filename+" "+self.cloud_storage_bucket
        print command 
        subprocess.check_output(command,shell=True)     