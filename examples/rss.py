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

#!/usr/bin/env python
"""
    Simple bullfrog example to pull down multiple rss feeds from
    in parallel, print out item headlines and if site was using http compression.
"""
import os,sys
from xml.dom.minidom import parse, parseString

import pathsetup
from client import ClientManager, Request

# Bullfrog Request
print "Create Client Manager"
client = ClientManager()
client.add_request(source='http://www.gamespot.com/rss/game_updates.php?', accept_compressed=True, timeout=2, nocache=True, key='Gamespot')
client.add_request(source='http://news.cnet.com/2547-1_3-0-20.xml', accept_compressed=True, nocache=True, key='News')
client.add_request(source='http://www.bnet.com/2408-11452_23-0.xml', nocache=True, key='The Insider')
result_set = client.execute()
print "Done executing Client Manager"

for r in result_set:
    if not r.exception:
        feed_dom = parseString(r.response_content) 
        for title in feed_dom.getElementsByTagName('title'):
                print r.key, "Headline: ", title.firstChild.data
        print "HTTP Compression Enabled: ", r.resp_was_compressed
        print "\n\n"
