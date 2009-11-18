#!/usr/bin/env python
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

"""
 The goal of this file is to serve as a functional example bullfrog ftp plugin.
"""

from bullfrog.client import ClientManager, Request
client = ClientManager()

kernel_archive_readme = Request(
    source = "ftp://ftp.kernel.org/",
    ftp_cwd="/pub/",
    username = "",
    password = "",
    # File Pattern is a REGEX
    ftp_file_pattern = "^README$",
    ftp_output_dir = "/tmp/ftp_downloads",
)    

kernel_manpages = Request ( 
    source = "ftp://ftp.kernel.org/",
    ftp_cwd="/pub/linux/docs/man-pages/",
    username = '',
    password = '',
    # File Pattern is a REGEX
    ftp_file_pattern = 'man-pages-3.16.tar.bz2$',
    ftp_output_dir = '/tmp/ftp_downloads',
)

client.add_request(kernel_archive_readme)
client.add_request(kernel_manpages)

client.execute()

print "Done, please check output directories for files"
