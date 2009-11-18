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

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

Version = 0.1
setup ( name='bullfrog',
        version = Version,
        description="Python framework to fetch content in parall",
        author = "Yousef Ourabi",
        author_email = "yourabi@gmail.com",
        url = "http://github.com/yourabi/bullfrog",
        packages = ['bullfrog', 'bullfrog.plugins'],
        license = 'Apache',
        platforms = 'Posix; MacOS X;',
        classifiers = ['Intended Audience :: Developers',
                       'License :: OSI Approved :: Apache License',
                       'Topic :: Internet :: WWW/HTTP',
                       'Topic :: Software Development :: Libraries :: Application Frameworks',
                       'Topic :: Software Development :: Libraries :: Python Modules',
                      ],
     )
