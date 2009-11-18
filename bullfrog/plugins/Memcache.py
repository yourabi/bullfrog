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


from time import time
import hashlib

try:
    import cPickle
except ImportError:
    import pickle


from bullfrog.backend import Backend


# Optional MC library.
try:
    import cmemcache as memcache
except ImportError:
    try:
        import memcache
    except ImportError:
        raise Exception("No Memcache Python Libraries installed or available")
        

class Memcache(Backend):
    """
        Memcache 
    """

    scheme = "memcache"
    backend_type = "backend"
    enabled = True

    # Should be configured to read fromn settings file instead of default
    def connect(self, debug=0, hosts=['127.0.0.1:11211',]):
        self.mc = memcache.Client(hosts, debug)
        self.is_cachable = False
    
    def fetch(self):
        pass

    def write(self, key, value, cache_ttl=600, threshold=86400):
        if len(value) > 2097152:
            raise CacheException("MemCache Cannot Cache greater than 2MB")
        
            
        if threshold > 86400:
            threshold = 86400
        
        total_timeout = cache_ttl + threshold
        
        if total_timeout > 86400:
            total_timeout = 86400
            
        key_version = "1" # TODO: read from settings.py to clear cache.
        versioned_key = hashlib.md5(key_version + "_" + key).hexdigest()
        
        tmp_tuple = (value, cache_ttl, threshold, time())
        pickled_cache_data = cPickle.dumps(tmp_tuple)
               
        self.mc.set(versioned_key, pickled_cache_data, total_timeout)
        
        # Return the generated cache key for reference. Might come in handy.
        return versioned_key

    def read(self, key):
        key_version = "1" # TODO: read for settings.py
        versioned_key = hashlib.md5(key_version + "_" + key).hexdigest()
        pickled_cache_value = self.mc.get(versioned_key)
        
        # The cached tuple contains all info for cache_ttl vs threshold.
        if pickled_cache_value:
            cached_tuple = cPickle.loads(pickled_cache_value)
            return cached_tuple
        return None
    
    def delete(self, key):
        self.mc.delete(key)
        
    def append(self, key, value):
        self.mc.append(key, value)
    
    def increment(self, key, delta=1):
        self.mc.incr(key,delta)
    
    def decrement(self, key, delta=1):
        self.mc.decr(key, delta)
