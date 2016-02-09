#! /usr/bin/env python

#
#    Copyright (C) 2016 Basho Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Riak Mesos Framework CLI"""

import json
import os
import sys
import time
import traceback
import requests
import commands
import constants
import util

from config import RiakMesosConfig


class RiakMesosCli(object):
    def __init__(self, cli_args):
        self.args = {}
        def_conf = '/etc/riak-mesos/config.json'
        cli_args, config_file = util.extract_option(cli_args, '--config', def_conf)
        cli_args, self.args.riak_file = util.extract_option(cli_args, '--file', '')
        cli_args, self.args.json_flag = util.extract_flag(cli_args, '--json')
        cli_args, self.args.help_flag = util.extract_flag(cli_args, '--help')
        cli_args, self.args.debug_flag = util.extract_flag(cli_args, '--debug')
        cli_args, self.args.cluster = util.extract_option(cli_args, '--cluster', 'default')
        cli_args, self.args.node = util.extract_option(cli_args, '--node', '')
        cli_args, self.args.bucket_type = util.extract_option(cli_args, '--bucket-type',
                                                         'default')
        args, self.args.props = util.extract_option(cli_args, '--props', '')
        args, num_nodes = util.extract_option(cli_args, '--nodes', '1', 'integer')
        self.args.num_nodes = int(num_nodes)
        self.cmd = ' '.join(cli_args)
        util.debug(self.args.debug_flag, 'Cluster: ' + self.args.cluster)
        util.debug(self.args.debug_flag, 'Node: ' + self.args.node)
        util.debug(self.args.debug_flag, 'Nodes: ' + str(self.args.num_nodes))
        util.debug(self.args.debug_flag, 'Command: ' + self.cmd)

        config = None
        if os.path.isfile(config_file):
            config = RiakMesosConfig(config_file)
        else:
            config = RiakMesosConfig()

        self.cfg = config

    def wait_for_framework(self, config, debug_flag, seconds):
        if seconds == 0:
            return False
        try:
            healthcheck_url = config.api_url() + 'clusters'
            if util.wait_for_url(healthcheck_url, debug_flag, 1):
                return True
        except:
            pass
        time.sleep(1)
        return self.wait_for_framework(config, debug_flag, seconds - 1)

    def wait_for_node(self, config, cluster, debug_flag, node, seconds):
        if self.wait_for_framework(config, debug_flag, 60):
            service_url = config.api_url()
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            util.debug_request(debug_flag, r)
            node_json = json.loads(r.text)
            node_host = node_json[node]['Hostname']
            node_port = str(node_json[node]['TaskData']['HTTPPort'])
            node_url = 'http://' + node_host + ':' + node_port
            if util.wait_for_url(node_url, debug_flag, 20):
                if node_json[node]['CurrentState'] == 3:
                    print('Node ' + node + ' is ready.')
                    return
                return self.wait_for_node(config, cluster, debug_flag, node,
                                          seconds - 1)
            print('Node ' + node + ' did not respond in 20 seconds.')
            return
        print('Riak Mesos Framework did not respond within 60 seconds.')
        return

    def node_info(config, cluster, debug_flag, node):
        service_url = config.api_url()
        r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
        util.debug_request(debug_flag, r)
        fw = config.get('framework-name')
        node_json = json.loads(r.text)
        http_port = str(node_json[node]['TaskData']['HTTPPort'])
        pb_port = str(node_json[node]['TaskData']['PBPort'])
        direct_host = node_json[node]['Hostname']
        mesos_dns_cluster = fw + '-' + cluster + '.' + fw + '.mesos'
        alive = False
        r = requests.get('http://' + direct_host + ':' + http_port)
        util.debug_request(debug_flag, r)
        if r.status_code == 200:
            alive = True
        node_data = {
            'http_direct': direct_host + ':' + http_port,
            'http_mesos_dns': mesos_dns_cluster + ':' + http_port,
            'pb_direct': direct_host + ':' + pb_port,
            'pb_mesos_dns': mesos_dns_cluster + ':' + pb_port,
            'alive': alive
        }
        return node_data

    def run(self):
        cmd_desc = help(self.cmd)

        if self.help_flag and not cmd_desc:
            print constants.usage
            return 0
        elif self.help_flag:
            print(cmd_desc)
            return 0

        if self.cmd == '':
            print('No commands executed')
            return
        elif self.cmd.startswith('-'):
            raise util.CliError('Unrecognized option: ' + self.cmd)
        elif not cmd_desc:
            raise util.CliError('Unrecognized command: ' + self.cmd)

        try:
            command_func_str = self.cmd.replace(' ', '_')
            command_func_str = command_func_str.replace('-', '_')
            command_func = getattr(commands, command_func_str)
            output = command_func(self.args, self.cfg)
            print output
        except AttributeError:
            raise util.CliError('Unrecognized command: ' + self.cmd)
        except requests.exceptions.ConnectionError as e:
            print('ConnectionError: ' + str(e))
            if self.debug_flag:
                traceback.print_exc()
                raise e
            return 1
        except util.CliError as e:
            print('CliError: ' + str(e))
            if self.debug_flag:
                traceback.print_exc()
                raise e
            return 1
        except Exception as e:
            print(e)
            if self.debug_flag:
                traceback.print_exc()
                raise e
            return 1

        return 0


def main():
    args = sys.argv[1:]
    if len(sys.argv) >= 2 and sys.argv[1] == 'riak':
        args = sys.argv[2:]
    if len(args) == 0:
        print constants.usage
        return 0
    if '--info' in args:
        print('Start and manage Riak nodes')
        return 0
    if '--version' in args:
        print('Riak Mesos Framework Version ' + constants.version)
        return 0
    if '--config-schema' in args:
        print('{}')
        return 0

    cli = RiakMesosCli(args)
    return cli.run()

if __name__ == '__main__':
    main()
