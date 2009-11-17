# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 

from backend import Backend
from socket import gethostbyname_ex, gethostbyname
import random

class DNS():
    """
    DNSCache handles caching the resolution of ips for hostnames to
    speed up common network fetches.
    """
    
    scheme = "dns"
    backend_type = "backend"
    enabled = True

    """
        Implement this to allow parallel dns resolutions similar to other backends.
    """
    def fetch(self):
        pass

    def resolve(self, hostname, cache):
        ip_address = None
        ip_cache_tuple = cache.read("dns_"+hostname)
        
        if ip_cache_tuple and len(ip_cache_tuple) > 0:
            ip_address = self.get_random_ip(ip_cache_tuple[0])
       
        # If ip is None there was a cache miss. Resolve and cache.
        if not ip_address:
            arecord = gethostbyname_ex(hostname)[2]
            cache.write("dns_%s" % hostname, arecord, cache_ttl=3600)
            ip_address = self.get_random_ip(arecord)

        return ip_address

    def get_random_ip(self, ip_list):
        ip_address = None
        
        if ip_list:
            random_index = random.randrange(0, len(ip_list))
            ip_address = ip_list[random_index]
        return ip_address
