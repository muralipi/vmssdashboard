import json

import azurerm


class vmss():
    def __init__(self, vmssname, vmssmodel, subscription_id, access_token):
        self.name = vmssname
        id = vmssmodel['id']
        self.rgname = id[id.index('resourceGroups/') + 15:id.index('/providers')]
        self.sub_id = subscription_id
        self.access_token = access_token

        self.model = vmssmodel
        self.capacity = vmssmodel['sku']['capacity']
        self.location = vmssmodel['location']
        self.vmsize = vmssmodel['sku']['name']
        self.tier = vmssmodel['sku']['tier']
        self.offer = vmssmodel['properties']['virtualMachineProfile']['storageProfile']['imageReference']['offer']
        self.sku = vmssmodel['properties']['virtualMachineProfile']['storageProfile']['imageReference']['sku']
        self.version = vmssmodel['properties']['virtualMachineProfile']['storageProfile']['imageReference']['version']
        self.provisioningState = vmssmodel['properties']['provisioningState']
        self.status = self.provisioningState

    # update the model, useful to see if provisioning is complete
    def refresh_model(self):
        vmssmodel = azurerm.get_vmss(self.access_token, self.sub_id, self.rgname, self.name)
        self.model = vmssmodel
        self.capacity = vmssmodel['sku']['capacity']
        self.vmsize = vmssmodel['sku']['name']
        self.version = vmssmodel['properties']['virtualMachineProfile']['storageProfile']['imageReference']['version']
        self.provisioningState = vmssmodel['properties']['provisioningState']
        self.status = self.provisioningState

    # update the token property
    def update_token(self, access_token):
        self.access_token = access_token

    # update the VMSS model version property
    def update_version(self, newversion):
        if self.version != newversion:
            self.model['properties']['virtualMachineProfile']['storageProfile']['imageReference'][
                'version'] = newversion
            self.version = newversion
            # put the vmss model
            updateresult = azurerm.update_vmss(self.access_token, self.sub_id, self.rgname, self.name,
                                               json.dumps(self.model))
            self.status = updateresult
        else:
            self.status = 'Versions are the same, skipping update'

    # set the VMSS to a new capacity
    def scale(self, capacity):
        self.model['sku']['capacity'] = capacity
        scaleoutput = azurerm.scale_vmss(self.access_token, self.sub_id, self.rgname, self.name, self.vmsize, self.tier,
                                         capacity)
        self.status = scaleoutput

    # power on all the VMs in the scale set
    def poweron(self):
        result = azurerm.start_vmss(self.access_token, self.sub_id, self.rgname, self.name)
        self.status = result

    # power off all the VMs in the scale set
    def poweroff(self):
        result = azurerm.poweroff_vmss(self.access_token, self.sub_id, self.rgname, self.name)
        self.status = result

    # stop deallocate all the VMs in the scale set
    def dealloc(self):
        result = azurerm.stopdealloc_vmss(self.access_token, self.sub_id, self.rgname, self.name)
        self.status = result

    # get the VMSS instance view and set the class property
    def init_vm_instance_view(self):
        # get an instance view list in order to build a heatmap
        self.vm_instance_view = \
            azurerm.list_vmss_vm_instance_view(self.access_token, self.sub_id, self.rgname, self.name)

    # operations on individual VMs or groups of VMs in a scale set
    def reimagevm(self, vmstring):
        result = azurerm.reimage_vmss_vms(self.access_token, self.sub_id, self.rgname, self.name, vmstring)
        self.status = result

    def upgradevm(self, vmstring):
        result = azurerm.upgrade_vmss_vms(self.access_token, self.sub_id, self.rgname, self.name, vmstring)
        self.status = result

    def deletevm(self, vmstring):
        result = azurerm.delete_vmss_vms(self.access_token, self.sub_id, self.rgname, self.name, vmstring)
        self.status = result

    def startvm(self, vmstring):
        result = azurerm.start_vmss_vms(self.access_token, self.sub_id, self.rgname, self.name, vmstring)
        self.status = result

    def restartvm(self, vmstring):
        result = azurerm.restart_vmss_vms(self.access_token, self.sub_id, self.rgname, self.name, vmstring)
        self.status = result

    def deallocvm(self, vmstring):
        result = azurerm.stopdealloc_vmss_vms(self.access_token, self.sub_id, self.rgname, self.name, vmstring)
        self.status = result

    def poweroffvm(self, vmstring):
        result = azurerm.poweroff_vmss_vms(self.access_token, self.sub_id, self.rgname, self.name, vmstring)
        self.status = result

    def get_power_state(self, statuses):
        for status in statuses:
            if status['code'].startswith('Power'):
                return status['code'][11:]

    # create a list of VMs in the scale set by fault domain and update domain
    def set_domain_lists(self):
        self.fd_dict = {f: [] for f in range(5)}
        self.ud_dict = {u: [] for u in range(5)}
        for instance in self.vm_instance_view['value']:
            try:
                instanceId = instance['instanceId']
                ud = instance['properties']['instanceView']['platformUpdateDomain']
                fd = instance['properties']['instanceView']['platformFaultDomain']
                power_state = self.get_power_state(instance['properties']['instanceView']['statuses'])
                self.ud_dict[ud].append([instanceId, power_state])
                self.fd_dict[fd].append([instanceId, power_state])
            except KeyError:
                print('KeyError: ' + json.dumps(instance))

