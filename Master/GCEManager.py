'''
Created on Jul 25, 2014

@author: cmelton
'''
from libcloud.compute.drivers.gce import GCENodeDriver
import urllib

class GCEManager(GCENodeDriver):
    '''
    This class is a subclass of GCENodeDriver with the added functionality of allowing
    service accounts in create_node
    '''
    def __init__(self, user_id, key, auth_account, datacenter=None, project=None,
                 auth_type=None, **kwargs):
#         print user_id, key
        self.auth_account = auth_account
        super(GCEManager, self).__init__(user_id, key, datacenter=datacenter, project=project, auth_type=auth_type, **kwargs)
    
    def _diskToDiskData(self, Disk):
        return {'kind': 'compute#attachedDisk',
                'boot': False,
                'type': 'pd-standard',
                #'mode': Disk.mode,
                'name': Disk.disk.name,
                'zone': Disk.disk.extra['zone'].extra['selfLink'],
                'source': Disk.disk.extra['selfLink']}
    
    def _disksToDiskData(self, Disks):
        return map(self._diskToDiskData, Disks)

    def list_nodes(self, ex_zone=None, regex=""):
        """
        Return a list of nodes in the current zone or all zones.

        :keyword  ex_zone:  Optional zone name or 'all'
        :type     ex_zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or ``None``

        :return:  List of Node objects
        :rtype:   ``list`` of :class:`Node`
        """
        list_nodes = []
        zone = self._set_zone(ex_zone)
        
        filter = ""
        if regex != "":
            filter="?filter=name"+urllib.quote(" eq '"+regex+"'", "")+"&"
        if zone is None:
            request = '/aggregated/instances'
        else:
            request = '/zones/%s/instances' % (zone.name)
        request+=filter
        print request


        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated response returns a dict for each zone
            if zone is None:
                for v in response['items'].values():
                    zone_nodes = [self._to_node(i) for i in
                                  v.get('instances', [])]
                    list_nodes.extend(zone_nodes)
            else:
                list_nodes = [self._to_node(i) for i in response['items']]
        return list_nodes
    
    def list_volumes(self, ex_zone=None, regex=""):
        """
        Return a list of volumes for a zone or all.

        Will return list from provided zone, or from the default zone unless
        given the value of 'all'.

        :keyword  ex_zone: The zone to return volumes from.
        :type     ex_zone: ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or ``None``

        :return: A list of volume objects.
        :rtype: ``list`` of :class:`StorageVolume`
        """
        list_volumes = []
        zone = self._set_zone(ex_zone)
        filter = ""
        if regex != "":
            filter="?filter=name"+urllib.quote(" eq '"+regex+"'", "")+"&"
        if zone is None:
            request = '/aggregated/disks'
        else:
            request = '/zones/%s/disks' % (zone.name)
        request+=filter
#         print request

        response = self.connection.request(request, method='GET').object
        if 'items' in response:
            # The aggregated response returns a dict for each zone
            if zone is None:
                for v in response['items'].values():
                    zone_volumes = [self._to_storage_volume(d) for d in
                                    v.get('disks', [])]
                    list_volumes.extend(zone_volumes)
            else:
                list_volumes = [self._to_storage_volume(d) for d in
                                response['items']]
        return list_volumes

    def localSSDData(self, location, numDisks=1):
        return [{#'kind': 'compute#attachedDisk',
                'autodelete': True,
                'type': 'SCRATCH', #'local-ssd',
#                 'type': 'local-ssd',
                'mode': 'READ_WRITE',
                'boot': False,
                "interface": "SCSI",
                'name': "local-ssd-"+str(i),
                'deviceName': "local-ssd-"+str(i),
                "initializeParams": {"diskType": "https://www.googleapis.com/compute/v1/projects/gbsc-gcp-lab-snyder/zones/us-central1-a/diskTypes/local-ssd"}
#"https://www.googleapis.com/compute/v1/projects/"+self.project+"/zones/"+location+"/diskTypes/local-ssd"}
                } for i in range(min(numDisks, 4))]
    
    def create_node(self, name, size, image, location=None,ex_network='default', 
                    ex_tags=None, ex_metadata=None,ex_boot_disk=None, 
                    use_existing_disk=True, external_ip='ephemeral', serviceAccountScopes=None, additionalDisks=[],
                    preemptible=False, numLocalSSD=0, log=None):
        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        if not hasattr(size, 'name'):
            size = self.ex_get_size(size, location)
        if not hasattr(ex_network, 'name'):
            ex_network = self.ex_get_network(ex_network)
        if not hasattr(image, 'name'):
            image = self.ex_get_image(image)

        if not ex_boot_disk:
            ex_boot_disk = self.create_volume(None, name, location=location,
                                              image=image,
                                              use_existing=use_existing_disk)

        request, node_data = self._create_node_req(name, size, image,
                                                   location, ex_network,
                                                   ex_tags, ex_metadata,
                                                   ex_boot_disk, external_ip)
        if serviceAccountScopes!=None:
            node_data["serviceAccounts"]=[{"scopes": serviceAccountScopes,
              "email": "default"}]
        for diskData in self._disksToDiskData(additionalDisks):
            node_data["disks"].append(diskData)
        if numLocalSSD>0:
            node_data["disks"]+=self.localSSDData(location)
        if preemptible:
            node_data["scheduling"]={'preemptible': True}
        if log != None:
            log.write("request: "+str(request))
            log.write("node data: "+str(node_data))
        print "request", request
        print "node data", str(node_data)
        self.connection.async_request(request, method='POST', data=node_data)

        return self.ex_get_node(name, location.name)