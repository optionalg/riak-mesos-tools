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

import util


def config(args, cfg):
    if args.json_flag:
        print(cfg.string())
    else:
        util.ppobj('Framework: ', cfg.string(), 'riak', '[]')
        util.ppobj('Director: ', cfg.string(), 'director', '[]')
        util.ppobj('Marathon: ', cfg.string(), 'marathon', '[]')


def framework(args, cfg):
    framework_cfg(args, cfg)


def framework_cfg(args, cfg):
    obj = cfg.framework_marathon_string()
    if json_flag:
        print(obj)
    else:
        ppobj('Marathon Cfg: ', obj, '', '{}')
    return

def framework_uninstall(args, cfg):
    print('Uninstalling framework...')
    fn = cfg.get('framework-name')
    client = create_client(cfg.get_any('marathon', 'url'))
    client.remove_app('/' + fn)
    print('Finished removing ' + '/' + fn + ' from marathon')
    return

def framework_clean_metadata(args, cfg):
    fn = cfg.get('framework-name')
    print('\nRemoving zookeeper information\n')
    result = cfg.zk_command('delete', '/riak/frameworks/' + fn)
    if result:
        print(result)
    else:
        print("Unable to remove framework zookeeper data.")
    return

def framework_teardown(args, cfg):
    r = requests.get('http://leader.mesos:5050/master/state.json')
    debug_request(debug_flag, r)
    if r.status_code != 200:
        print('Failed to get state.json from master.')
        return
    js = json.loads(r.text)
    for fw in js['frameworks']:
        if fw['name'] == cfg.get('framework-name'):
            r = requests.post(
                'http://leader.mesos:5050/master/teardown',
                data='frameworkId='+fw['id'])
            debug_request(debug_flag, r)
            print('Finished teardown.')
    return

def proxy_cfg(args, cfg):
    proxy(args, cfg)


def proxy(args, cfg):
    print(cfg.director_marathon_string(cluster))
    return


def proxy_install(args, cfg):
    director_json = cfg.director_marathon_json(cluster)
    client = create_client(cfg.get_any('marathon', 'url'))
    client.add_app(director_json)
    print('Finished adding ' + director_json['id'] + ' to marathon.')
    return

def proxy_uninstall(args, cfg):
    client = create_client(cfg.get_any('marathon', 'url'))
    fn = cfg.get('framework-name')
    client.remove_app('/' + fn + '-director')
    print('Finished removing ' + '/' + fn + '-director' +
          ' from marathon')
    return

def proxy_endpoints(args, cfg):
    client = create_client(cfg.get_any('marathon', 'url'))
    app = client.get_app(cfg.get('framework-name') + '-director')
    task = app['tasks'][0]
    ports = task['ports']
    hostname = task['host']
    print('Load Balanced Riak Cluster (HTTP)')
    print('    http://' + hostname + ':' + str(ports[0]))
    print('Load Balanced Riak Cluster (Protobuf)')
    print('    http://' + hostname + ':' + str(ports[1]))
    print('Riak Mesos Director API (HTTP)')
    print('    http://' + hostname + ':' + str(ports[2]))
    return


def framework_install(args, cfg):
    framework_json = cfg.framework_marathon_json()
    client = create_client(cfg.get_any('marathon', 'url'))
    client.add_app(framework_json)
    print('Finished adding ' + framework_json['id'] + ' to marathon.')
    return


def framework_wait_for_service(args, cfg):
    if wait_for_framework(cfg, debug_flag, 60):
        print('Riak Mesos Framework is ready.')
        return
    print('Riak Mesos Framework did not respond within 60 seconds.')
    return


def node_wait_for_service(args, cfg):
    if node == '':
        raise utils.CliError('Node name must be specified')
    wait_for_node(cfg, cluster, debug_flag, node, 20)
    return

def cluster_wait_for_service(args, cfg):
    if wait_for_framework(cfg, debug_flag, 60):
        service_url = cfg.api_url()
        r = requests.get(service_url + 'clusters/' + cluster +
                         '/nodes')
        debug_request(debug_flag, r)
        js = json.loads(r.text)
        for k in js.keys():
            wait_for_node(cfg, cluster, debug_flag, k, 20)
            return
        print('Riak Mesos Framework did not respond within 60 '
              'seconds.')
    return


def cluster_endpoints(args, cfg):
    if wait_for_framework(cfg, debug_flag, 60):
        service_url = cfg.api_url()
        r = requests.get(service_url + 'clusters/' + cluster +
                         '/nodes')
        debug_request(debug_flag, r)
        if r.status_code == 200:
            js = json.loads(r.text)
            cluster_data = {}
            for k in js.keys():
                cluster_data[k] = node_info(cfg, cluster,
                                            debug_flag, k)
                print(json.dumps(cluster_data))
            else:
                print(r.text)
                return
            print('Riak Mesos Framework did not respond within 60 '
                  'seconds.')
        return


def proxy_wait_for_service(args, cfg):
    if wait_for_framework(cfg, debug_flag, 60):
        client = create_client(cfg.get_any('marathon', 'url'))
        app = client.get_app(cfg.get('framework-name') +
                             '-director')
        if len(app['tasks']) == 0:
            print("Proxy is not installed.")
            return
        task = app['tasks'][0]
        ports = task['ports']
        hostname = task['host']
        if util.wait_for_url('http://' + hostname + ':' +
                             str(ports[0]), debug_flag, 20):
            print("Proxy is ready.")
            return
        print("Proxy did not respond in 20 seconds.")
        return
    print('Riak Mesos Framework did not respond within 60 seconds.')
    return


def framework_endpoints(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    print("Framework HTTP API: " + service_url)
    return


def cluster_cfg(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if riak_file == '':
        r = requests.get(service_url + 'clusters/' + cluster)
        debug_request(debug_flag, r)
        if r.status_code == 200:
            ppfact('riak.conf: ', r.text, 'RiakCfg',
                   'Error getting cluster.')
        else:
            print('Cluster not created.')
            return
        with open(riak_file) as data_file:
            r = requests.post(service_url + 'clusters/' + cluster +
                              '/cfg', data=data_file)
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to set riak.conf, status_code: ' +
                      str(r.status_code))
            else:
                print('riak.conf updated')
    return
def cluster_cfg_advanced(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if riak_file == '':
        r = requests.get(service_url + 'clusters/' + cluster)
        debug_request(debug_flag, r)
        if r.status_code == 200:
            ppfact('advanced.cfg: ', r.text, 'AdvancedCfg',
                   'Error getting cluster.')
        else:
            print('Cluster not created.')
            return
        with open(riak_file) as data_file:
            r = requests.post(service_url + 'clusters/' + cluster +
                              '/advancedCfg', data=data_file)
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to set advanced.cfg, status_code: ' +
                      str(r.status_code))
            else:
                print('advanced.cfg updated')
        return


def cluster_list(args, cfg):
    cluster(args, cfg)


def cluster(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.get(service_url + 'clusters')
    debug_request(debug_flag, r)
    if r.status_code == 200:
        if json_flag:
            print(r.text)
        else:
            pparr('Clusters: ', r.text, '[]')
    else:
        print('No clusters created')
    return


def cluster_create(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.post(service_url + 'clusters/' + cluster, data='')
    debug_request(debug_flag, r)
    if r.text == '' or r.status_code != 200:
        print('Cluster already exists.')
    else:
        ppfact('Added cluster: ', r.text, 'Name',
               'Error creating cluster.')
    return


def cluster_restart(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.post(service_url + 'clusters/' + cluster + '/restart',
                      data='')
    debug_request(debug_flag, r)
    if r.status_code == 404:
        print('Cluster does not exist.')
    elif r.status_code != 202:
        print('Failed to restart cluster, status code: ' +
              str(r.status_code))
    else:
        print('Cluster restart initiated.')
    return


def cluster_destroy(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.delete(service_url + 'clusters/' + cluster, data='')
    debug_request(debug_flag, r)
    if r.status_code != 202:
        print('Failed to destroy cluster, status_code: ' +
              str(r.status_code))
    else:
        print('Destroyed cluster: ' + cluster)
    return


def node_list(args, cfg):
    node(args, cfg)


def node(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
    debug_request(debug_flag, r)
    if json_flag:
        print(r.text)
    else:
        pparr('Nodes: ', r.text, '[]')
    return


def node_info(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
    debug_request(debug_flag, r)
    node_json = json.loads(r.text)
    print('HTTP: http://' + node_json[node]['Hostname'] + ':' +
          str(node_json[node]['TaskData']['HTTPPort']))
    print('PB  : ' + node_json[node]['Hostname'] + ':' +
          str(node_json[node]['TaskData']['PBPort']))
    ppobj('Node: ', r.text, node, '{}')
    return


def node_add(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    for x in range(0, num_nodes):
        r = requests.post(service_url + 'clusters/' + cluster +
                          '/nodes', data='')
        debug_request(debug_flag, r)
        if r.status_code != 200:
            print(r.text)
        else:
            ppfact('New node: ' + cfg.get('framework-name') + '-' +
                   cluster + '-', r.text, 'SimpleId', 'Error adding '
                   'node')
    return


def node_remove(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if node == '':
        raise CliError('Node name must be specified')
    r = requests.delete(service_url + 'clusters/' + cluster +
                        '/nodes/' + node, data='')
    debug_request(debug_flag, r)
    if r.status_code != 202:
        print('Failed to remove node, status_code: ' +
              str(r.status_code))
    else:
        print('Removed node')
    return


def node_aae_status(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if node == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                     node + '/aae')
    debug_request(debug_flag, r)
    if r.status_code != 200:
        print('Failed to get aae-status, status_code: ' +
              str(r.status_code))
    else:
        ppobj('', r.text, 'aae-status', '{}')
    return


def node_status(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if node == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                     node + '/status')
    debug_request(debug_flag, r)
    if r.status_code != 200:
        print('Failed to get status, status_code: ' +
              str(r.status_code))
    else:
        ppobj('', r.text, 'status', '{}')
    return


def node_ringready(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if node == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                     node + '/ringready')
    debug_request(debug_flag, r)
    if r.status_code != 200:
        print('Failed to get ringready, status_code: ' +
              str(r.status_code))
    else:
        ppobj('', r.text, 'ringready', '{}')
    return


def node_transfers(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if node == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                     node + '/transfers')
    debug_request(debug_flag, r)
    if r.status_code != 200:
        print('Failed to get transfers, status_code: ' +
              str(r.status_code))
    else:
        ppobj('', r.text, 'transfers', '{}')
    return


def node_bucket_type_create(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if node == '' or bucket_type == '' or props == '':
        raise CliError('Node name, bucket-type, props must be '
                       'specified')
    r = requests.post(service_url + 'clusters/' + cluster + '/nodes/' +
                      node + '/types/' + bucket_type, data=props)
    debug_request(debug_flag, r)
    if r.status_code != 200:
        print('Failed to create bucket-type, status_code: ' +
              str(r.status_code))
        ppobj('', r.text, '', '{}')
    else:
        ppobj('', r.text, '', '{}')
    return


def node_bucket_type_list(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if node == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                     node + '/types')
    debug_request(debug_flag, r)
    if r.status_code != 200:
        print('Failed to get bucket types, status_code: ' +
              str(r.status_code))
    else:
        ppobj('', r.text, 'bucket_types', '{}')
    return
