from pathlib import Path
import subprocess
import unittest


class BlankVolumeTest(unittest.TestCase):
    def run_probe(self, body):
        script = Path(__file__).with_name('prepare-volume.sh').resolve()
        command = 'source "$1"\nwipefs() { '+body+'; }\nrequire_no_signatures /task-disk\nprintf passed'
        return subprocess.run(['bash', '-c', command, 'test', str(script)], capture_output=True, text=True)

    def test_empty_success_requires_correct_output_option(self):
        result = self.run_probe('[[ "$*" == "--no-act --noheadings --output TYPE /task-disk" ]]')
        self.assertEqual((result.returncode, result.stdout), (0, 'passed'))

    def test_failed_probe_cannot_authorize_formatting(self):
        result = self.run_probe('return 1')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('passed', result.stdout)

    def test_existing_signature_cannot_authorize_formatting(self):
        result = self.run_probe('printf ext4')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('passed', result.stdout)


if __name__ == '__main__': unittest.main()
