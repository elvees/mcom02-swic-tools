This directory contains host environment and tools for analyzing SpaceWire
performance. Tools are run via SSH on remote MCom-02 `Salute-EL24PM`__ board
installed on `Salute-EL24OM1`__ board, copies raw data back to host and analyzes
the data (e.g. plots graphs). SWIC0, SWIC1 SpaceWire controllers must
be connected to each other. Salute-EL24PM must be flashed with Buildroot > v3.1.

__ http://multicore.ru/index.php?id=1389
__ http://multicore.ru/index.php?id=1390

Prepare host environment::

  pip3 install setuptools pip virtualenv --user -U
  pip3 install pipenv --user -U
  export PATH=~/.local/bin:$PATH

Initialize Python environment::

  pipenv install -r requirements.txt

Run analysis::

  make TARGET_IP=<device-ip-or-hostname>

