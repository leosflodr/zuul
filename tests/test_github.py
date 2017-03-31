# Copyright 2015 GoodData
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

import logging
import re
from testtools.matchers import MatchesRegex

from tests.base import ZuulTestCase

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-32s '
                    '%(levelname)-8s %(message)s')


class TestGithub(ZuulTestCase):

    def setup_config(self, config_file='zuul-github.conf'):
        super(TestGithub, self).setup_config(config_file)

    def test_pull_event(self):
        self.worker.registerFunction('set_description:' +
                                     self.worker.worker_id)

        self.worker.hold_jobs_in_build = True

        pr = self.fake_github.openFakePullRequest('org/project', 'master')
        self.fake_github.emitEvent(pr.getPullRequestOpenedEvent())
        self.waitUntilSettled()

        build_params = self.builds[0].parameters
        self.assertEqual('master', build_params['ZUUL_BRANCH'])
        self.assertEqual(str(pr.number), build_params['ZUUL_CHANGE'])
        self.assertEqual(pr.head_sha, build_params['ZUUL_PATCHSET'])

        self.worker.hold_jobs_in_build = False
        self.worker.release()
        self.waitUntilSettled()

        self.assertEqual('SUCCESS',
                         self.getJobFromHistory('project-merge').result)
        self.assertEqual('SUCCESS',
                         self.getJobFromHistory('project-test1').result)
        self.assertEqual('SUCCESS',
                         self.getJobFromHistory('project-test2').result)

        descr = self.getJobFromHistory('project-merge').description
        self.assertThat(descr, MatchesRegex(
            r'.*<\s*a\s+href='
            '[\'"]https://github.com/org/project/pull/%s[\'"]'
            '\s*>%s,%s<\s*/a\s*>' %
            (pr.number, pr.number, pr.head_sha),
            re.DOTALL
        ))
        self.assertEqual(1, len(pr.comments))
