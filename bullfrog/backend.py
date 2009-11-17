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

import threading
from time import time

# Migrate towards httplib for flexibility
import httplib

from urlparse import urlparse
import urllib
import urllib2
from urllib2 import URLError, HTTPError
from ftplib import FTP
from socket import gethostbyname_ex, gethostbyname

# Compressed/Gzipped responses.
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
    
import gzip
import pprint
import re

class Backend(threading.Thread):
    """
     Backend class. All plugins inherit from this.
     Implements threading so that plugins are transparently multi-threaded.
    """

    def __init__(self, request):
        
        self.request = request
        threading.Thread.__init__(self)
       
        # Rethink this whole block.
        self.nocache = self.request.global_nocache
        self.recache = self.request.global_recache
        self.accept_compressed = self.request.global_accept_compressed
        self.cache_ttl = self.request.cache_ttl
        
        # Properties of Request override globals set at ClientManager level.
        if hasattr(self.request, "nocache") and self.request.nocache is not self.nocache:
            self.nocache = self.request.nocache
        if hasattr(self.request, "recache") and self.request.recache is not self.recache:
            self.recache = self.request.recache
        if hasattr(self.request, "accept_compressed") and self.request.accept_compressed is not self.accept_compressed:
            self.accept_compressed = self.request.accept_compressed

        if hasattr(self.request, "solr_root"):
            self.solr_root = self.request.solr_root
        
    def run(self):
        """
        Called via parent thread
        If you want to run in a serial context just call backend.fetch()
        """
        self.fetch()
        
    def fetch(self):
        """
        This is implemented by each of the Backend (sub-classes) plugins: Http, Ftp...etc
        """

    def validate(self):
        """
        This will eventually be part of the interface plugins will need to
        implement. For now it is a no-op. This was originally on the request,
        but it makes more sense to have it on the "server-side".
        """
