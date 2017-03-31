# Copyright 2012 Hewlett-Packard Development Company, L.P.
# Copyright 2013 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import json
import logging
import re
import threading
import time
from paste import httpserver
import webob
from webob import dec

"""Zuul main web app.

Zuul supports HTTP requests directly against it for determining the
change status. These responses are provided as json data structures.

The supported urls are:

 - /status: return a complex data structure that represents the entire
   queue / pipeline structure of the system
 - /status.json (backwards compatibility): same as /status
 - /status/change/X,Y: return status just for gerrit change X,Y

When returning status for a single gerrit change you will get an
array of changes, they will not include the queue structure.
"""


class WebApp(threading.Thread):
    log = logging.getLogger("zuul.WebApp")
    change_path_regexp = '/status/change/(\d+,\d+)$'

    def __init__(self, scheduler, port=8001, cache_expiry=1,
                 listen_address='0.0.0.0'):
        threading.Thread.__init__(self)
        self.scheduler = scheduler
        self.listen_address = listen_address
        self.port = port
        self.cache_expiry = cache_expiry
        self.cache_time = 0
        self.cache = None
        self.daemon = True
        self.routes = {}
        self._init_default_routes()
        self.server = httpserver.serve(
            dec.wsgify(self.app), host=self.listen_address, port=self.port,
            start_loop=False)

    def _init_default_routes(self):
        self.register_path('/(status\.json|status)$', self.status)
        self.register_path(self.change_path_regexp, self.change)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.server_close()

    def _changes_by_func(self, func):
        """Filter changes by a user provided function.

        In order to support arbitrary collection of subsets of changes
        we provide a low level filtering mechanism that takes a
        function which applies to changes. The output of this function
        is a flattened list of those collected changes.
        """
        status = []
        jsonstruct = json.loads(self.cache)
        for pipeline in jsonstruct['pipelines']:
            for change_queue in pipeline['change_queues']:
                for head in change_queue['heads']:
                    for change in head:
                        if func(change):
                            status.append(copy.deepcopy(change))
        return json.dumps(status)

    def _status_for_change(self, rev):
        """Return the statuses for a particular change id X,Y."""
        def func(change):
            return change['id'] == rev
        return self._changes_by_func(func)

    def register_path(self, path, handler):
        path_re = re.compile(path)
        self.routes[path] = (path_re, handler)

    def unregister_path(self, path):
        if self.routes.get(path):
            del self.routes[path]

    def app(self, request):
        for path_re, handler in self.routes.itervalues():
            if path_re.match(request.path):
                return handler(request)
        else:
            raise webob.exc.HTTPNotFound()

    def status(self, request):
        def func():
            return webob.Response(body=self.cache,
                                  content_type='application/json')
        return self._response_with_status_cache(func)

    def change(self, request):
        def func():
            m = re.match(self.change_path_regexp, request.path)
            change_id = m.group(1)
            status = self._status_for_change(change_id)
            if status:
                return webob.Response(body=status,
                                      content_type='application/json')
            else:
                raise webob.exc.HTTPNotFound()
        return self._response_with_status_cache(func)

    def _refresh_status_cache(self):
        if (not self.cache or
            (time.time() - self.cache_time) > self.cache_expiry):
            try:
                self.cache = self.scheduler.formatStatusJSON()
                # Call time.time() again because formatting above may take
                # longer than the cache timeout.
                self.cache_time = time.time()
            except:
                self.log.exception("Exception formatting status:")
                raise

    def _response_with_status_cache(self, func):
        self._refresh_status_cache()

        response = func()

        response.headers['Access-Control-Allow-Origin'] = '*'
        response.cache_control.public = True
        response.cache_control.max_age = self.cache_expiry
        response.last_modified = self.cache_time
        response.expires = self.cache_time + self.cache_expiry

        return response.conditional_response_app
