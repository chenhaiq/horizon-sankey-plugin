# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 B1 Systems GmbH
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django.utils.translation import ugettext_lazy as _

from django import http
from django.utils import simplejson as json

from horizon import exceptions
from horizon import tables
from horizon.utils import functions as utils
from openstack_dashboard import api
from openstack_dashboard.dashboards.admin.sankey \
    import tables as project_tables

class SankeyIndexView(tables.DataTableView):
    table_class = project_tables.AdminHypervisorsTable
    template_name = 'admin/sankey/index.html'

    def get_data(self):
        pass

    def get_context_data(self, **kwargs):
        pass

NAME = "name"
CPU = "cpu"
MEMORY = "memory"
DISK = "disk"

SOURCE = "source"
TARGET = "target"
VALUE = "value"
TYPE = "type"
        
class SankeyJsonView(tables.DataTableView):
    table_class = project_tables.AdminHypervisorsTable
    template_name = 'admin/sankey/index.html'

    def render_to_response(self, context):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        return http.HttpResponse(content,
                                 content_type='application/json',
                                 **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        return json.dumps(context["stats"])

    def get_data(self):
        pass

    def __get_scalers(self, hypervisors):
        sum_memory = sum_disk = sum_cpu = 0.0
        for hypervisor in hypervisors:
            sum_memory += hypervisor.memory_mb
            sum_cpu    += hypervisor.vcpus
            sum_disk   += hypervisor.local_gb
        base_value = sum_cpu
        return {CPU    : base_value/sum_cpu,
                MEMORY : base_value/sum_memory,
                DISK   : base_value/sum_disk}
        
    def get_context_data(self, **kwargs):
        context = super(SankeyJsonView, self).get_context_data(**kwargs)

        try:
            flavors = api.nova.flavor_list(self.request)
            hypervisors = api.nova.hypervisor_list(self.request)
            # TODO check has_more_data
            instances, has_more_data = api.nova.server_list(self.request, None, True)

            hypervisors_list = []
            scalers = self.__get_scalers(hypervisors)
            
            for hypervisor in hypervisors:
                index = 0
                hostInfo = {}
                nodes = []
                links = []
                hypervisors_list.append({"nodes": nodes, "links": links})
                
                # init hypervsior nodes
                nodes.append({NAME: hypervisor.hypervisor_hostname})
                hypervisorIndex = index

                index +=1
                nodes.append({NAME: CPU,
                              TYPE: CPU})
                links.append({SOURCE: index, TARGET: hypervisorIndex, 
                              VALUE: hypervisor.vcpus * scalers[CPU],
                              TYPE: CPU})
                cpuIndex = index

                index +=1
                nodes.append({NAME: MEMORY,
                              TYPE: MEMORY})
                links.append({SOURCE: index, TARGET: hypervisorIndex, 
                              VALUE: hypervisor.memory_mb * scalers[MEMORY],
                              TYPE: MEMORY})
                memoryIndex = index

                index +=1
                nodes.append({NAME: DISK,
                              TYPE: DISK})
                links.append({SOURCE: index, TARGET: hypervisorIndex, 
                              VALUE: hypervisor.local_gb * scalers[DISK],
                              TYPE: DISK})
                diskIndex = index                
                index +=1
                
                for inst in instances:
                    if getattr(inst, 'OS-EXT-SRV-ATTR:host') == hypervisor.hypervisor_hostname:
                        flavor_id = inst.flavor["id"]
                        nodes.append({NAME: inst.name})
        
                        for flavor in flavors:
                            if flavor_id == flavor.id:
                                links.append({SOURCE: index, 
                                                TARGET: cpuIndex, 
                                                VALUE: flavor.vcpus * scalers[CPU],
                                                TYPE: CPU})
                                links.append({SOURCE: index, 
                                                TARGET: memoryIndex, 
                                                VALUE: flavor.ram * scalers[MEMORY],
                                                TYPE: MEMORY})
                                links.append({SOURCE: index, 
                                                TARGET: diskIndex,
                                                VALUE: flavor.disk * scalers[DISK],
                                                TYPE: DISK})
                                break
                        index +=1
                
            context["stats"] = {"hypervisors": hypervisors_list, "scalers": scalers}
        except Exception:
            exceptions.handle(self.request,
                _('Unable to retrieve hypervisor statistics.'))
        return context
