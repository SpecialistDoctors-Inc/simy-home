"""Installation must distinguish an existing container from its network."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class InstallRuntimeTest(unittest.TestCase):
    def test_network_name_does_not_block_stopped_container_upgrade(self):
        source = Path(__file__).with_name('install-runtime.sh').read_text()
        guard = source[source.index('if docker '):source.index('\nrunner=')]
        with tempfile.TemporaryDirectory() as directory:
            docker = Path(directory) / 'docker'
            docker.write_text('''#!/bin/sh
if [ "$1" = container ] && [ "$2" = inspect ] && [ "$3" = hp-agent ]; then
  [ "$EXISTING_CONTAINER" = yes ]; exit $?
fi
# Generic inspect also finds the pre-existing hp-agent network.
if [ "$1" = inspect ] && [ "$2" = hp-agent ]; then exit 0; fi
exit 2
''')
            docker.chmod(0o755)
            env = {**os.environ, 'PATH': directory + ':' + os.environ['PATH']}
            for exists, expected in [('no', 0), ('yes', 1)]:
                with self.subTest(container=exists):
                    result = subprocess.run(['bash', '-c', guard],
                                            env={**env, 'EXISTING_CONTAINER': exists},
                                            capture_output=True, text=True)
                    self.assertEqual(expected, result.returncode)
