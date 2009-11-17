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
import urllib2
import httplib
from urllib2 import URLError, HTTPError
import sys

from urlparse import urlparse

from cStringIO import StringIO
import gzip

import logging
import re
import socket

from backend import Backend

class Http(Backend):

    """
    As the name implies this backend plugin is responsible for HTTP requests.
    """
    
    scheme = "http"
    backend_type = 'backend'
    enabled = True

    def fetch(self):
        
        # For testing only.
        if self.request.fail_flag:
            self.request.exception = Exception("Timeout")
            return

        self.request_parser()
        
        # timers
        cache_read_time = None
        cache_write_time = None
        
        # Threshold stuff. Tuple returned from cache, and content is what
        # is ultimately returned to the user.
        cache_is_fresh = False
        content = None
        
        decompression_time = None
        
        self.request.resp_was_compressed = False
        self.request.is_redirected = False
        
        # Note: both of these can be true when recache flag is true.
        cache_hit = False # Was content pulled from a cache source or not.
        cache_write = False # Did we write anything to cache?

        # handle / apply global overrides
        if self.request.global_overrides:
            self.nocache = self.request.global_nocache
            self.recache = self.request.global_recache
        
        
        # Log all redirects up to maximum. Array of Redirect Dictionaries
        # Dictionary contains all header information.
        # Pending rewrite to httplib.
        # redirect_chain = []

        # Only skip cache read if nocache flag is true
        cache_tuple = None
        content_tuple = None
        if not self.nocache:
            cache_read_time_start = time()
            cache_tuple = self.request.cache.read(self.request.source)
            cache_read_time_stop = time() 
            cache_read_time = cache_read_time_stop - cache_read_time_start
            
            
            # Other half of cache threshold implementation.
            current_time = time()
            backend_tuple = None
            

            # print >> sys.stderr, 'Cache Tuple: ', cache_tuple
            if cache_tuple:
                content_tuple = cache_tuple[0]
                if cache_tuple[1] + cache_tuple[3] > current_time:
                    cache_is_fresh = True
                else:
                    cache_tuple = None
           
            # Check threshold is within limit. If not, fetch.
            if content_tuple and cache_is_fresh:
                content = content_tuple[0]
                response_headers = content_tuple[1]
                response_code = content_tuple[2]
                response_time = content_tuple[3]
                cache_hit = True
                

            
        # IF cache miss, or recache flag is true fetch content and cache.
        if self.recache or not cache_tuple or not cache_is_fresh:
            
                # Use IP from DNS Cache lookup. I should add an off flag.
                new_source = StringIO()
                new_source.write('http://')
                new_source.write(self.request.ip)
                if self.request.port:
                    new_source.write(':' + str(self.request.port))
                new_source.write(self.request.path)
                
                if self.request.query:
                    new_source.write('?')
                    new_source.write(self.request.query)
                
                ip_source = new_source.getvalue()
                request = urllib2.Request(ip_source)      

                # Add Host header so that when using ip from DNS cache
                # The correct VHOST is hit on the remote server.
                request.add_unredirected_header('Host', self.request.hostname)
                request.add_header('Accept', 'text/html, text/plain')
                request.add_header('User-Agent', 'Bullfrog +http://github.com/yourabi/bullfrog')

                
                if hasattr(self.request, 'headers'):
                    for header in self.request.headers:
                        if header.lower() == "host":
                            request.add_unredirected_header(header, self.request.headers[header])
                        else:
                            request.add_header(header, self.request.headers[header])
                
                # TODO: Is this really correct?
                if hasattr(self.request, "accept_compressed") and self.request.accept_compressed or self.request.global_accept_compressed:
                    request.add_header('Accept-Encoding', 'gzip,compress,deflate')
               
                http_response = None
                while not http_response and self.request.retry_count <= self.request.retries:
                    #print "LOOP OUTER"
                    try:
                        #print "TOP OF REQUEST LOOP"
                        
                        ### MEAT OF REQUEST
                        opener = urllib2.build_opener(RedirectHandler)
                        # opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))
                        fetch_start = time()
                        if self.request.body is not None:
                            if hasattr(self.request, "encoding"):
                                self.request.body = self.request.body.encode(self.request.encoding)
                        http_response = opener.open(request, self.request.body, self.request.timeout)

                        http_body = http_response.read()
                        fetch_stop = time()
                       
                        # Store redirect.
                        if not http_response.geturl() == ip_source:
                            self.request.is_redirected = True
                            self.request.redirect_url = http_response.geturl()
                            

                        ### END MEAT OF REQUEST

                        # Handle Compressed/Gzipped responses even if we didn't
                        # send a gzipped request.
                        if self.response_is_compressed(http_response):
                            self.request.resp_was_compressed = True
                            http_body, decompression_time = self.decompress(http_body)

                        # VALIDATION/INVALIDATION, REALLY THINK THIS THROUGH FOOL
                        if not self.regex_validate_response(body=http_body):
                            # If we know the request is now invalid set nocache and set a flag.
                            # self.nocache = True
                            self.request.regex_invalidated = 1 
                            http_response = None
                            raise Exception('Regex Invalidated Response Body')

                        content = http_body
                        response_code = http_response.getcode()
                        response_headers = http_response.headers.dict
                        response_time = fetch_stop - fetch_start
                
                        # Handle recache with non 200 response
                        if not skip_cache_write and not self.nocache and response_code == 200:
                            cache_tuple = (content, response_headers, response_code, response_time)
                            cache_write_time_start = time()
                            self.request.cache.write(self.request.source, cache_tuple, self.request.cache_ttl)
                            cache_write_time_stop = time()
                            cache_write_time = cache_write_time_stop - cache_write_time_start
                            cache_write = True


                    # Move Exception stuff up in here.
                    # This previously set a bunch of the expected attributes to None
                    # However, I believe a more correct solution is to modify the
                    # Request objects descriptor so that __get__ checks for exceptions
                    # Double Check that this will cactch HTTP errors (500) as well as network timeout.
                    except Exception as error:
                        # Only retry hit if we don't have long-cache
                        if content_tuple:
                            content = content_tuple[0]
                            response_headers = content_tuple[1]
                            response_code = content_tuple[2]
                            response_time = content_tuple[3]
                            cache_hit = True
                            break
                        
                        # We have no long cache, retry network hit.
                        else:
                            self.request.retry_count += 1
                            if not self.request.retry_count <= self.request.retries:
                                self.request.network_error = 1
                                self.request.exception = error
                                return
                            else:
                                continue

        # Threshold check.
        # This is end of successful flow.
        self.request.response_content = content
        self.request.response_code = response_code
        self.request.response_headers = response_headers
        self.request.response_time = response_time
        self.request.cache_hit = cache_hit
        self.request.cache_is_fresh = cache_is_fresh
        self.request.cache_write = cache_write
        self.request.decompression_time = decompression_time        
        self.request.cache_read_time = cache_read_time
        self.request.cache_write_time = cache_write_time
        self.request.exception = None # Another check clients can do.
        
        return
    
    def decompress(self, compressed_string):
        start_compress = time()
        compressed_stream = StringIO(compressed_string)
        gzipper = gzip.GzipFile(fileobj=compressed_stream)
        uncompressed_data = gzipper.read()
        stop_compress = time()
        return (uncompressed_data, stop_compress - start_compress)
    
    # TODO: this seems flawed. Multiple content-encodings?
    def response_is_compressed(self, response):
        is_compressed = False        
        if 'content-encoding' in response.headers:
            is_compressed = True
        return is_compressed

    def request_parser(self):
        parsed = urlparse(self.request.source)
        self.request.hostname = parsed.hostname
        self.request.port = parsed.port
        self.request.scheme = parsed.scheme
        
        # DNS Resolution
        self.request.ip = self.request.dns_cache.resolve(self.request.hostname, self.request.cache)
        
        self.request.path = parsed.path
        self.request.query = parsed.query


    # Check array of regular expressions that signal invalid response
    # if true, might consider setting nocache to true and setting some flag.
    def regex_invalidate_response(self,body=None):
        is_invalid = False 
        if hasattr(self.request, 'regex_invalidators'):
            for regex in self.request.regex_invalidators:
                if re.search(regex, body):
                    is_invalid = True 
        return is_invalid

    # Cleanup this logic since it is essentially same as invalidate
    def regex_validate_response(self, body=None):
        if hasattr(self.request, 'regex_validators'):
            is_valid = False
            for regex in self.request. regex_validators:
                if re.search(regex,body):
                    is_valid = True
        else:
            # Since nothing to validate, assume true.
            is_valid = True
            

        return is_valid
    
# Handle number of hops, tracking previous urls...etc
class RedirectHandler(urllib2.HTTPRedirectHandler):

    max_repeats = 2
    max_redirections = 2
    orig_info_msg = urllib2.HTTPRedirectHandler.inf_msg

    def set_max_repeats(self, repeats):
        self.max_repeates = repeats
        self.inf_msg = "Custom Number of Redirects exceeded"

    def set_max_redirections(self, redirections):
        self.max_redirections = redirections
        self.inf_msg = "Custom Number of Redirects exceeded"


class HTTPErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        pass
   
