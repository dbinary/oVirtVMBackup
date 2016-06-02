from __future__ import print_function

from lxml import etree
from progress.spinner import Spinner
from ovirtsdk.api import API
from ovirtsdk.infrastructure.errors import ConnectionError, RequestError
from ovirtsdk.xml import params
from colorama import Fore


class OvirtBackup():
    """Class for export and import Virtual Machine in oVirt/RHEV environment"""
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password

    def print_info(self):
        print(self.url)
        print(self.user)
        print(self.password)

    def connect(self):
        """Connect to oVirt/RHEV API"""
        try:
            self.api = API(url=self.url, username=self.user,
                           password=self.password, insecure='True')
            return self.api
        except RequestError as err:
            print("Error: {} Reason: {}".format(err.status, err.reason))
            exit(0)

    def create_snap(self, desc, vm):
        """Create a snapshot from a virtual machine with params:
            @param desc: Description of Snapshot
            @param vm: Virtual Machine Name
        """
        try:
            self.api.vms.get(vm).snapshots.add(params.Snapshot(description=desc, vm=self.api.vms.get(vm)))
            self.snapshot = self.api.vms.get(vm).snapshots.list(description=desc)[0]
            self.__wait_snap(vm, self.snapshot.id)
        except RequestError as err:
            print("Error: {} Reason: {}".format(err.status, err.reason))
            exit(-1)

    def __wait_snap(self, vm, id_snap):
        """ Time wait while create a snapshot of a Virtual Machine"""
        spinner = Spinner(Fore.YELLOW + "waiting for snapshot to finish... ")
        while self.api.vms.get(vm).snapshots.get(id=id_snap).snapshot_status != "ok":
            spinner.next()

    def __wait(self, vm, action):
        """Time wait while create and export of a Virtual Machine"""
        if action == '0':
            self.action = "creation"
        elif action == '1':
            self.action = "export"
        spinner = Spinner(Fore.YELLOW + "waiting for vm {}... ".format(self.action))
        while self.get_vm_status(vm) != 'down':
            spinner.next()

    def delete_snap(self, desc, vm):
        """Delete a snapshot from a virtual machine with params:
            @param desc: Description of Snapshot
            @param vm: Virtual Machine Name
        """
        try:
            self.snapshot = self.api.vms.get(vm).snapshots.list(description=desc)[0]
            self.snapshot.delete()
        except RequestError as err:
            print("Error: {} Reason: {}".format(err.status, err.reason))
            exit(-1)

    def get_ovf(self, vm, desc):
        """Get ovf info from snapshot"""
        try:
            self.snapshot = self.api.vms.get(vm).snapshots.list(
                all_content=True, description=desc)[0]
            self.ovf = self.snapshot.get_initialization().get_configuration().get_data()
            self.root = etree.fromstring(self.ovf)
            with open(vm + '.ovf', 'w') as ovfFile, open( vm + ".xml", 'w') as xmlFile:
                ovfFile.write(self.ovf)
                xmlFile.write(etree.tostring(self.root, pretty_print=True))
        except RequestError as err:
            print("Error: {} Reason: {}".format(err.status, err.reason))
            exit(-1)

    def create_vm_to_export(self, vm, new_name, desc):
        try:
            self.snapshot = self.api.vms.get(vm).snapshots.list(description=desc)[0]
            self.snapshots = params.Snapshots(snapshot=[params.Snapshot(id=self.snapshot.id)])
            self.cluster = self.api.clusters.get(id=self.api.vms.get(vm).cluster.id)
            self.api.vms.add(
                params.VM(
                    name=new_name, snapshots=self.snapshots,
                    cluster=self.cluster, template=self.api.templates.get(name="Blank")))
            self.__wait(new_name,'0')
        except RequestError as err:
            print("Error: {} Reason: {}".format(err.status, err.reason))
            exit(0)

    def get_export_domain(self, vm):
        """Return Export Domain
            :param vm: Virtual Machine Name
        """
        self.cluster = self.api.clusters.get(id=self.api.vms.get(vm).cluster.id)
        self.dc = self.api.datacenters.get(id=self.cluster.data_center.id)

        self.export = None

        for self.sd in self.dc.storagedomains.list():
            if self.sd.type_ == "export":
                self.export = self.sd
        return self.export

    def get_storage_domains(self,vm):
        self.datacenter = self.get_dc(vm)
        return self.datacenter.storagedomains.list()

    def get_dc(self, vm):
        """Return Datacenter object
            :param vm: Virtual Machine Name
        """
        self.dc = self.api.datacenters.get(id=self.get_cluster(vm).data_center.id)
        return self.dc

    def get_cluster(self, vm):
        """Return Cluster object
            :param vm: Virtual Machine Name
        """
        self.cluster = self.api.clusters.get(id=self.api.vms.get(vm).cluster.id)
        return self.cluster

    def if_exists_vm(self, vm):
        """Verify if virtual machine and new virtual machine already exists"""
        if (self.api.vms.get(vm)):
            return 1
        else:
            return 0

    def get_vm_status(self, vm):
        """Verify status of virtual machine"""
        self.state = self.api.vms.get(vm).status.state
        return self.state

if __name__ == '__main__':
    print("This file is intended to be used as a library of functions and it's not expected to be executed directly")
