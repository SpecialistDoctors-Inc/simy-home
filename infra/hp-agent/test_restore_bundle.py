import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('restore_bundle',Path(__file__).with_name('restore-bundle.py'))
restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)


class RestoreTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_preserves_only_expected_owner_and_strips_special_mode(self):
        member=tarfile.TarInfo('codex-auth/auth.json');member.uid=1000;member.gid=1000;member.mode=0o4600
        result=restore.safe_member(member,self.temp.name)
        self.assertEqual((result.uid,result.gid,result.mode),(1000,1000,0o600))

    def test_rejects_escape_and_unexpected_root(self):
        for name in ['../escape','/etc/passwd','work/../../escape','other/file']:
            with self.subTest(name=name),self.assertRaises(ValueError):
                restore.safe_member(tarfile.TarInfo(name),self.temp.name)

    def test_rejects_links_special_files_and_unexpected_owner(self):
        for kind in [tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE,tarfile.CHRTYPE]:
            member=tarfile.TarInfo('work/link');member.type=kind
            with self.assertRaises(ValueError):restore.safe_member(member,self.temp.name)
        member=tarfile.TarInfo('control/config.json');member.uid=501
        with self.assertRaises(ValueError):restore.safe_member(member,self.temp.name)


if __name__=='__main__':unittest.main()
