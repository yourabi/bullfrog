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

import os
import sys
import re
from urlparse import urlparse
from time import time
from datetime import datetime

import logging
import logging.handlers

from pluginslib import Plugins
from plugins import Memcache, DNS

class ClientManager(object):
    """
    This is the point of interaction for bullfrog. The basic work flow is to 
    instantiate a client manager and add requests to its queue by calling
    add_request(). Once all desired requests have been added call execute()
    to hit the network. If you want to reuse the client manager to make another
    request call reset() to clear any internal state.
    
    ClientManager is responsible for loading any plugins and setting up state.

    Settings: MEMCACHED_SERVERS, Debug Flag, (Bullfrog Log File)
    
    Example:
        r = ClientManager()
        r.add_request(source='http://cnn.com')
        request = Request(source='http://google.com')
        r.add_request(request)
        responses = r.execute()
        
        for resp in responses:
            print resp.response_body

        r.reset()
        r...
    """
    
    def __init__(self, nocache=False, 
                       recache=False,
                       accept_compressed=True,
                       global_overrides=False, ):

        # This should get passed around. Like the village bicycle.
        plugin_load_start = time()
        self.plugins = Plugins()
        plugin_load_stop = time()
        
        # Various ways to access soon-to-be populated requests.
        self.requests = []
        self.requests_by_key = {}
        
        self.threads = []
        self.timers = {}
        self.logging_data = {}        
       
        # Logging levels.
        LEVELS = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
       
        
        # Global cache control Settings, can override at request level.
        self.nocache = nocache
        self.recache = recache
        self.accept_compressed = accept_compressed
        self.global_overrides = global_overrides
        
    def execute(self, parallel=True):
        total_runtime_start = time()
        for request in self.requests:     

                
            # Backend via request needs to be aware of global vs request 
            # overrides.
            request.global_nocache = self.nocache
            request.global_recache = self.recache
            request.global_accept_compressed = self.accept_compressed
            request.global_overrides = self.global_overrides


            cache_setup_start = time()
            request.cache = Memcache.Memcache(request)
            request.cache.connect()
            request.dns_cache = DNS.DNS()
            cache_setup_stop = time()
            self.timers['cache_setup'] = cache_setup_stop - cache_setup_start
            
            scheme = self.parse_scheme(request)
            if scheme in self.plugins.scheme_to_plugin:
                backend = self.plugins.scheme_to_plugin[scheme](request)
            else:
                print >> sys.stderr, "No backend plugin found aborting: ", request.source
                
            # If running in parallel, call start which is method of Thread
            # whith then internally delegates to run()
            if parallel:
                self.threads.append(backend)
                backend.start()
            else:
                backend.run()

        # Make sure all threads finish before returning.
        for t in self.threads:
            t.join()        
        
        total_runtime_stop = time()
        self.timers['total_runtime'] = total_runtime_stop - total_runtime_start

        for request in self.requests:
            # this totally breaks with FTP.
            response_time = '-'
            if hasattr(request, 'response_time'):
                response_time = request.response_time
            
            exception_msg = ''
            timed_out = 0
            if hasattr(request, 'exception'):
                if re.search("timed out", str(request.exception)):
                    timed_out=1
                exception_msg = request.exception
                
                if not exception_msg:
                    exception_msg = ''
            
            content_length = 0
            if request.response_content:
                content_length = len(str(request.response_content))

            # Make it easy to get requests by name
            if hasattr(request, 'key'):
                self.requests_by_key[request.key] = request
                            
        return self.requests


    def get_request_by_key(self, name):
        return self.requests_by_key.get(name, None)
            
    def add_request(self, *args, **kwargs):
        """
            adds a request object to the request manager queue.  
            
            If the first parameter is not of type "Request", it assumes the arguments 
            being passed in are for the Request object constructor and passes them 
            through via kwargs.
        """       
        if len(args) > 0 and isinstance(args[0], Request): 
            self.requests.append(args[0])
        else:
            self.requests.append(Request(**kwargs))


    def reset(self):
        """
        Resets the client to ready it for reuse.
        """

        self.requests = []
        self.requests_by_key = {}


    # Parse out scheme from request URI and lookup scheme to plugin map.
    def parse_scheme(self, request):
        match = re.search('^([^://])+', request.source)
        scheme = None
        if match:
            scheme = match.group(0)
        return scheme
        
class Request(object):
    """
    The Request object encapsulates the source and optional parameters for a
    backend plugin.
    """

    def __init__(self, *args, **kwargs):
        """
        Request constructor takes arbitrary keyword argument but only certain
        keywords are used/affect system. 
        
        Required Arguments:
            source
        
        Universal Arguments
            source
            nocache=False
            recache=False
            cache_ttl=60
            timeout=5
            username=None
            password=None
            name=None

        HTTP Backend Arguments
            accept_compressed=True|False
            method=get,put,post,delete,head
            body=string
            headers=dictionary
            encoding=string (e.g. "utf-8")
        
        FTP Backend Arguments
            cwd
            output_dir
            file_pattern
        
        Examples:
            request = Request(source="http://google.com")
        """

        # Default timeout/cache timeout settings.
        self.cache_ttl = 60
        self.cache_threshold = 86400
        self.timeout = 5
        self.body = None # Post Body, required by urllib2
        self.encode = True
        self.response_content = None
        self.retries = 1 
        self.fail_flag = False

        # Clobber any defaults with user-specified values.
        for key in kwargs:
            setattr(self, key, kwargs[key])

        # Immutable Stuff, used for reporting on the way back out.
        self.retry_count = 0
        self.regex_invalidated = 0 
        self.network_error = 0 
        self.exception = None
            
                     
    @apply
    def url():
        def fget(self):
            if hasattr(self, 'source'):
                return self.source
            else:
                return None
        def fset(self, value):
            self.source = value
        return property(**locals())
    
    @apply
    def body():
        def fget(self):
            if hasattr(self, '_body'):
                return self._body
            else:
                return None
        def fset(self, value):
            self._body = value
            if value:
                self.nocache = True
        return property(**locals())


class RequestException(Exception):
    def __init__(self, backend=None, reason=None):
        self.reason = reason
        self.backend = backend
        
    def __repr__(self):
        return '%s Backend Failed becasue %s' % (self.backend, self.reason)
    
    def __str__(self):
        return '%s Backend Failed becasue %s' % (self.backend, self.reason)

