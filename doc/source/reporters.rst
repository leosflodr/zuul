:title: Reporters

Reporters
=========

Zuul can communicate results and progress back to configurable
protocols. For example, after succeeding in a build a pipeline can be
configured to post a positive review back to Gerrit.

There are three stages when a report can be handled. That is on:
Start, Success or Failure. Each stage can have multiple reports.
For example, you can set verified on Gerrit and send an email.

Gerrit
------

Zuul works with standard versions of Gerrit by invoking the
``gerrit`` command over an SSH connection.  It reports back to
Gerrit using SSH.

The dictionary passed to the Gerrit reporter is used for ``gerrit
review`` arguments, with the boolean value of ``true`` simply
indicating that the argument should be present without following it
with a value. For example, ``verified: 1`` becomes ``gerrit review
--verified 1`` and ``submit: true`` becomes ``gerrit review
--submit``.

A :ref:`connection` that uses the gerrit driver must be supplied to the
trigger.

GitHub
------

Zuul reports back to GitHub pull requests via GitHub API.
On success and failure, it creates a comment containing the build results.
It also sets the status on start, success and failure. Status name and
description is taken from the pipeline.

A :ref:`connection` that uses the github driver must be supplied to the
reporter. It has the following options.

  **status**
  Boolean value (``true`` or ``false``) that determines if the reporter should
  set commit status on github. Defaults to ``false``.
  ``commit_status=true``

  **comment**
  Boolean value (``true`` or ``false``) that determines if the reporter should
  add a comment with the pipeline status to the github pull request.
  Defaults to ``false``.
  ``comment=true``

  **merge**
  Boolean value (``true`` or ``false``) that determines if the reporter should
  merge the pull reqeust. Defaults to ``false``.
  ``merge=false``

  **label**
  List of strings each representing an exact label name which should be added
  to the pull request by reporter. To remove a label by reporter prepend a dash
  to the label name. Defaults to empty list.
  ``label: 'test successful'``
  ``label: '-test failed'``


SMTP
----

A simple email reporter is also available.

A :ref:`connection` that uses the smtp driver must be supplied to the
reporter.

SMTP Configuration
~~~~~~~~~~~~~~~~~~

zuul.conf contains the SMTP server and default to/from as described
in :ref:`zuulconf`.

Each pipeline can overwrite the ``subject`` or the ``to`` or ``from`` address by
providing alternatives as arguments to the reporter. For example, ::

  pipelines:
    - name: post-merge
      manager: IndependentPipelineManager
      source: my_gerrit
      trigger:
        my_gerrit:
          - event: change-merged
      success:
        outgoing_smtp:
          to: you@example.com
      failure:
        internal_smtp:
          to: you@example.com
          from: alternative@example.com
          subject: Change {change} failed

SQL
---

This reporter is used to store results in a database.

A :ref:`connection` that uses the sql driver must be supplied to the
reporter.

SQL Configuration
~~~~~~~~~~~~~~~~~

zuul.conf contains the database connection and credentials. To store different
reports in different databases you'll need to create a new connection per
database.

The sql reporter is used to store the results from individual builds rather
than the change. As such the sql reporter does nothing on "start" or
"merge-failure".

**score**
  A score to store for the result of the build. eg: -1 might indicate a failed
  build similar to the vote posted back via the gerrit reporter.

For example ::

  pipelines:
    - name: post-merge
      manager: IndependentPipelineManager
      source: my_gerrit
      trigger:
        my_gerrit:
          - event: change-merged
      success:
        mydb_conn:
            score: 1
      failure:
        mydb_conn:
            score: -1
