#!/usr/bin/env python2

import sys
import re
import argparse
import json
import requests

from gevent import monkey
from managers import EventManager, ThreadManager
from proxy_handlers import GatherProxyHandler, ProxyIPListHandler, AliveProxyHandler,\
    CoolProxyHandler, ProxyNovaHandler, ProxyHTTPHandler, CheckerProxyHandler, FreeProxyListHandler


monkey.patch_all()
sys.tracebacklimit = 0


CONFIG = json.load(open('config.json'))

def parse_args():
    """
    Creating an ArgumentParser

    :return: ArgumentParser
    """

    parser = argparse.ArgumentParser(
        description='Free proxy Search'
    )
    group = parser.add_mutually_exclusive_group(
        required=True
    )

    parser.add_argument(
        '-o',
        '--output',
        default='proxies.json',
        help='Output JSON file (e.g, exemple.json)'
    )
    group.add_argument(
        '--aliveproxy',
        default=False,
        action='store_true',
        help='Get proxies from aliveproxy.com'
    )
    group.add_argument(
        '--checkerproxy',
        default=False,
        action='store_true',
        help='Get proxies from checkerproxy.net'
    )
    group.add_argument(
        '--coolproxy',
        default=False,
        action='store_true',
        help='Get proxies from cool-proxy.net'
    )
    group.add_argument(
        '--freeproxylist',
        default=False,
        action='store_true',
        help='Get proxies from freeproxylists.com'
    )
    group.add_argument(
        '--gatherproxy',
        default=False,
        action='store_true',
        help='Get proxies from gatherproxy.com'
    )
    group.add_argument(
        '--proxyhttp',
        default=False,
        action='store_true',
        help='Get proxies from proxyhttp.net'
    )
    group.add_argument(
        '--proxyiplist',
        default=False,
        action='store_true',
        help='Get proxies from proxy-ip-list.com'
    )
    group.add_argument(
        '--proxynova',
        default=False,
        action='store_true',
        help='Get proxies from proxynova.com'
    )
    group.add_argument(
        '--all',
        default=False,
        action='store_true',
        help='Get proxies from all sites'
    )
    parser.add_argument(
        '--all-no',
        default=[],
        help='All proxies except'
    )
    parser.add_argument(
        '--check',
        default=False,
        action='store_true',
        help='Verify the proxies is working'
    )

    try:
        return parser.parse_args()
    except SystemExit:
        sys.exit(0)


class GetProxies(EventManager):

    def __init__(self, args):
        super(GetProxies, self).__init__()
        self.args = vars(args)
        self.proxies = []
        self.headers = {'User-Agent': CONFIG['agent']}
        self.current_ip = None

    def run(self):
        """
        Start class GetProxies
        """

        self.log('GetProxies initialized')

        self.current_ip = self.get_current_ip()
        self.log(
            'Your Current IP: \033[93m{}'.format(
                self.current_ip
            )
        )

        all_no = []
        if len(self.args['all_no']):
            all_no = map(str, self.args['all_no'].split(','))

        if self.args['gatherproxy'] or self.args['all'] and 'gatherproxy' not in all_no:
            self.proxies.append(
                GatherProxyHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        if self.args['proxyiplist'] or self.args['all'] and 'proxyiplist' not in all_no:
            self.proxies.append(
                ProxyIPListHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        if self.args['aliveproxy'] or self.args['all'] and 'aliveproxy' not in all_no:
            self.proxies.append(
                AliveProxyHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        if self.args['coolproxy'] or self.args['all'] and 'coolproxy' not in all_no:
            self.proxies.append(
                CoolProxyHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        if self.args['proxynova'] or self.args['all'] and 'proxynova' not in all_no:
            self.proxies.append(
                ProxyNovaHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        if self.args['proxyhttp'] or self.args['all'] and 'proxyhttp' not in all_no:
            self.proxies.append(
                ProxyHTTPHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        if self.args['checkerproxy'] or self.args['all'] and 'checkerproxy' not in all_no:
            self.proxies.append(
                CheckerProxyHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        if self.args['freeproxylist'] or self.args['all'] and 'freeproxylist' not in all_no:
            self.proxies.append(
                FreeProxyListHandler(
                    self.log,
                    self.headers
                ).initialize()
            )

        self.proxies = [ips for proxy in self.proxies for ips in proxy]
        self.proxies = {proxy['ip']: proxy for proxy in self.proxies}.values()

        self.log(
            'Total Unic Proxies Find: \033[93m{}'.format(
                len(self.proxies)
            )
        )

        if self.args['check']:
            self.log('Testing Proxies...')
            self.start_proxy_checker()
        else:
            self.log('Saving Proxies...')
            self.save_proxy(self.proxies)

    def get_current_ip(self):
        """
        Obtain the current IP

        :return: String your current IP
        """

        try:
            resp = requests.get('http://checkip.amazonaws.com', headers=self.headers, timeout=15)
            return resp.text.replace('\n', '')
        except requests.exceptions.Timeout:
            self.log('Timeout error to check your current IP', 'ERROR', True)
            sys.exit(1)
        except requests.exceptions.RequestException:
            self.log('An HTTP error occurred in check your current ip', 'ERROR', True)
            sys.exit(1)
        except Exception as err:
            self.log(str(err), 'ERROR', True)
            sys.exit(1)

    def start_proxy_checker(self):
        """
        Start threads to check proxies

        :return:
        """

        threads = []
        results = []

        if len(self.proxies) >= 100:
            proxies = (
                self.proxies[i:i + len(self.proxies) / 100]
                for i in xrange(0, len(self.proxies), len(self.proxies) / 100)
            )
        else:
            proxies = (
                self.proxies[i:i + len(self.proxies) / 10]
                for i in xrange(0, len(self.proxies), len(self.proxies) / 10)
            )

        for pxs in proxies:
            threads.append(
                ThreadManager(
                    target=self.checker,
                    args=(
                        pxs,
                    )
                )
            )

        for thread in threads:
            thread.start()

        try:
            for thread in threads:
                results.append(thread.join())
        except KeyboardInterrupt:
            self.log('Ctrl-C caught, exiting', 'WARNING', True)
            sys.exit(1)

        result = [x for i in results for x in i]
        self.save_proxy(result)

        self.log('Total Working Proxies: \033[93m{}'.format(len(result)))

    def checker(self, proxies):
        """
        Check proxy is functional

        :param proxies: List of proxies
        :return: Array proxies checked
        """

        result = []
        for proxy in proxies:
            try:
                resp = requests.get('http://checkip.amazonaws.com',
                                    headers=self.headers,
                                    proxies={
                                        'http': '{}:{}'.format(proxy['ip'], proxy['port']),
                                        'https': '{}:{}'.format(proxy['ip'], proxy['port'])
                                    },
                                    timeout=15)
            except:
                continue

            if resp.status_code == 200:
                ip_checked = self.ip_check(resp.text)
                if ip_checked:
                    proxy['ms'] = str(resp.elapsed)
                    result.append(proxy)
                    self.log('Checking Proxy \033[93m{}'.format(proxy['ip']), 'SUCCESS')
        return result

    def ip_check(self, html):
        """
        Verifies that the IP received on self.test_proxy is the same as the proxy

        :param html: Response text
        :return: True or False
        """

        html_lines = html.splitlines()
        ip_re = '(?:[0-9]{1,3}\.){3}[0-9]{1,3}'

        if len(html_lines) == 1:
            match = re.match(ip_re, html)
            if match:
                if self.current_ip in html:
                    return False
            else:
                return False
        else:
            return False

        return True

    def save_proxy(self, proxies):
        """
        Save proxies in JSON file

        :param proxies: Array proxies
        :return:
        """

        with open(self.args['output'], "w") as f:
            json.dump(proxies, f)


start = GetProxies(parse_args())
start.run()
