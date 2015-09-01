#!/usr/bin/python
# -*- coding: utf-8 -*- #
#
# Copyright 2015 Nandaja Varma <nvarma@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from yaml_writer import YamlWriter
from conf_parser import ConfigParseHelpers
from global_vars import Global
from helpers import Helpers


class GaneshaManagement(YamlWriter):

    def __init__(self, config):
        self.config = config
        self.get_ganesha_data()


    def get_ganesha_data(self):
        try:
            self.section_dict = self.config._sections['nfs-ganesha']
            del self.section_dict['__name__']
        except:
            return
        action = self.section_dict.get('action')
        if not action:
            print "\nWarning: Section 'nfs-ganesha' without any action option " \
                    "found. Skipping this section!"
            return
        del self.section_dict['action']
        self.section_dict = self.fix_format_of_values_in_config(self.section_dict)
        action_func = { 'create-cluster': self.create_cluster,
                        'destroy-cluster': self.destroy_cluster,
                        'export-volume': self.export_volume,
                        'unexport-volume': self.unexport_volume
                      }[action]
        if not action_func:
            print "\nError: Unknown action provided for nfs-ganesha. Exiting!\n"\
                    "Supported actions are: [create-cluster, destroy-cluster,"\
                    "export-volume, unexport-volume]"
            self.cleanup_and_quit()
        action_func()
        self.filename = Global.group_file
        self.iterate_dicts_and_yaml_write(self.section_dict)


    def create_cluster(self):
        if not self.section_dict['ha_name']:
            self.section_dict['ha_name'] = 'ganesha-ha-360'

        cluster = []
        self.check_for_param_presence('cluster_nodes', self.section_dict)
        cluster_nodes = self.section_dict.get('cluster_nodes')
        cluster = self.pattern_stripping(cluster_nodes)
        if not set(cluster).issubset(set(Global.hosts)):
            print "\nError: 'cluster_nodes' for nfs-ganesha should be " \
                   "subset of the 'hosts'. Exiting!"
            self.cleanup_and_quit()

        self.write_config('cluster_nodes', cluster, Global.inventory)
        self.write_config('master_node', [cluster[0]], Global.inventory)
        self.section_dict['cluster_hosts'] = ','.join(node for node in cluster)
        self.section_dict['master_node'] = cluster[0]

        self.get_host_vips(cluster)

        Global.playbooks.append('bootstrap-nfs-ganesha.yml')
        if not self.section_dict.get('volname'
                ) or self.present_in_yaml(Global.group_file, 'volname'):
            self.export_volume()


    def get_host_vips(self, cluster):
        self.check_for_param_presence('VIPs', self.section_dict)
        VIPs = self.pattern_stripping(self.section_dict.get('VIPs'))
        if len(cluster) != len(VIPs):
            print "\nError: The number of cluster_nodes provided and VIPS "\
                    "given doesn't match. Exiting!"
            self.cleanup_and_quit()
        self.section_dict['VIPs'] = VIPs
        vip_list = []
        for host, vip in zip(cluster, VIPs):
            key = 'VIP_' + host
            vip_list.append("%s=\"%s\"" %(key, vip))
        VIPs = '\n'.join(vip_list)
        self.section_dict['vip_list'] = VIPs

    def export_volume(self):
        Global.playbooks.append('ganesha-volume-configs.yml')
        Global.playbooks.append('gluster-shared-volume-mount.yml')
        Global.playbooks.append('gluster-volume-export-ganesha.yml')

    def destroy_cluster(self):
        return

    def unexport_volume(self):
        return