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

import Queue, bisect

# Should only be loaded once by clients
class Plugins(object):
    # Store quick references to different types of plugins.
    
    def __init__(self):
        self.scheme_to_plugin = {}  # Map http -> Http.py
        self.scheme_to_name = {}
        self.cacheable_plugins = {} # List of backends that consent to caching
        self.library = []           # All backends
        
        # Make sure plugins are on PYTHONPATH
        root_path = os.path.abspath(os.path.dirname(__file__))
        path = os.path.abspath(root_path + '/' + 'plugins')
        if path not in sys.path:
            sys.path.append(path)

        # Do some validation of plugins and reject ones that don't comform to
        # the backend protocol.
        for file in os.listdir(path):
            module_name, ext = os.path.splitext(file) # Handles no-extension files, etc.
            
            if ext == '.py': # Important, ignore .pyc/other files.
                module = __import__(module_name)
               
                if module.__name__ in module.__dict__:
                    real_plugin = module.__dict__[module.__name__]
                    self.scheme_to_plugin[real_plugin.scheme] = real_plugin
                    self.scheme_to_name[real_plugin.scheme] = real_plugin.__name__
                    
                    self.library.append(real_plugin)
