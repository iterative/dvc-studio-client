DVC Studio Client
=================

Client to interact with `DVC Studio`_.

|PyPI| |Status| |Python Version| |License|

|Tests| |Codecov| |pre-commit| |Black|

.. |PyPI| image:: https://img.shields.io/pypi/v/dvc-studio-client.svg
   :target: https://pypi.org/project/dvc-studio-client/
   :alt: PyPI
.. |Status| image:: https://img.shields.io/pypi/status/dvc-studio-client.svg
   :target: https://pypi.org/project/dvc-studio-client/
   :alt: Status
.. |Python Version| image:: https://img.shields.io/pypi/pyversions/dvc-studio-client
   :target: https://pypi.org/project/dvc-studio-client
   :alt: Python Version
.. |License| image:: https://img.shields.io/pypi/l/dvc-studio-client
   :target: https://opensource.org/licenses/Apache-2.0
   :alt: License
.. |Tests| image:: https://github.com/iterative/dvc-studio-client/workflows/Tests/badge.svg
   :target: https://github.com/iterative/dvc-studio-client/actions?workflow=Tests
   :alt: Tests
.. |Codecov| image:: https://codecov.io/gh/iterative/dvc-studio-client/branch/main/graph/badge.svg
   :target: https://app.codecov.io/gh/iterative/dvc-studio-client
   :alt: Codecov
.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black

Features
--------

- Model Registry
   - `get_download_uris`_: Return download URIs for the specified model.

- Live Experiments
   - `post_live_metrics`_: Post updates to `api/live`.

Installation
------------

You can install *DVC Studio Client* via pip_ from PyPI_:

.. code:: console

   $ pip install dvc-studio-client

License
-------

Distributed under the terms of the `Apache 2.0 license`_,
*DVC Studio Client* is free and open source software.


Issues
------

If you encounter any problems,
please `file an issue`_ along with a detailed description.


.. _Apache 2.0 license: https://opensource.org/licenses/Apache-2.0
.. _PyPI: https://pypi.org/
.. _file an issue: https://github.com/iterative/DVC Studio Client/issues
.. _pip: https://pip.pypa.io/
.. github-only
.. _Contributor Guide: CONTRIBUTING.rst
.. _DVC Studio: https://dvc.org/doc/studio
.. _get_download_uris: https://docs.iterative.ai/dvc-studio-client/reference/dvc_studio_client/model_registry/
.. _post_live_metrics: https://docs.iterative.ai/dvc-studio-client/reference/dvc_studio_client/post_live_metrics/
