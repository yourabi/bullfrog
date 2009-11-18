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

import re

from ftplib import FTP
from urlparse import urlparse
from bullfrog.backend import Backend

class Ftp(Backend):
    
    scheme = 'ftp'
    backend_type = 'backend'
    enabled = True
        
    def fetch(self):
        self.request_parser()
        
        if not hasattr(self.request, "ftp_cwd"):
            self.request.ftp_cwd = "/"
            
        """ Grok any arguments and suck down content """
        files = []

        ftp = FTP(self.request.hostname)
        ftp.login(self.request.username, self.request.password)
        ftp.cwd(self.request.ftp_cwd)
            
        ftp.dir(files.append)
        for f in files:
            file_name = re.split('\s+', f)[8]
            if re.match(self.request.ftp_file_pattern, file_name):
                self._get_binary(ftp, file_name)

        ftp.quit()

    def _get_binary(self, ftp, filename):
        out = self.request.ftp_output_dir + "/" + filename
        ftp.retrbinary('RETR ' + filename, open(out, 'wb').write)


    def validate(self):
        '''
        '''
        pass

    def request_parser(self):
        parsed = urlparse(self.request.source)
        self.request.hostname = parsed.hostname
        self.request.port = parsed.port
        self.request.scheme = parsed.scheme
        self.request.ip = self.request.dns_cache.resolve(self.request.hostname, self.request.cache)
        self.request.path = parsed.path
        self.request.query = parsed.query
