from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SOURCE = Path(__file__).parents[1] / "src" / "airar.py"


def load_module():
    spec = importlib.util.spec_from_file_location("smart_unpacker_regression", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ImmediateRoot:
    def after(self, _delay, callback, *args):
        callback(*args)


class DummyVar:
    def set(self, _value):
        pass


def make_app(module):
    app = module.SmartUnpackerGUI.__new__(module.SmartUnpackerGUI)
    app.root = ImmediateRoot()
    app.is_processing = True
    app.password_for_run = "fixture-password"
    app.last_output_dir = None
    app.progress_var = DummyVar()
    app.stats_vars = {}
    app.stats = {
        "archives_found": 0,
        "archives_extracted": 0,
        "files_renamed": 0,
        "errors": 0,
        "deleted_archives": 0,
        "merged_folders": 0,
    }
    app.initial_input_files = set()
    app.successfully_extracted_archives = set()
    app.logs = []
    app.log_message = app.logs.append
    app.update_stats = lambda: None
    return app


class MultiVolumeRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_folder_processes_only_first_rar_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index in (1, 2, 3):
                (root / f"6347.part{index}.rar").write_bytes(b"Rar!\x1a\x07\x01\x00fixture")
            app = make_app(self.module)
            attempted = []
            app.restore_and_extract = lambda path, _ext: attempted.append(Path(path).name) or None
            app.cleanup_extracted_results = lambda _root: True
            app.unpack_nested_archives(root)
            self.assertEqual(attempted, ["6347.part1.rar"])

    def test_password_avoids_noninteractive_no_password_switch(self):
        class FakePatool:
            kwargs = None

            @classmethod
            def extract_archive(cls, _archive, **kwargs):
                cls.kwargs = kwargs
                Path(kwargs["outdir"]).mkdir(parents=True)

        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "single.rar"
            archive.write_bytes(b"Rar!\x1a\x07\x01\x00fixture")
            app = make_app(self.module)
            original = self.module.patoolib
            self.module.patoolib = FakePatool
            try:
                result = app.restore_and_extract(archive, ".rar")
            finally:
                self.module.patoolib = original
            self.assertIsNotNone(result)
            self.assertIs(FakePatool.kwargs["interactive"], True)
            self.assertEqual(FakePatool.kwargs["password"], "fixture-password")

    def test_cleanup_preserves_preexisting_rar_volumes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            volumes = []
            for index in (1, 2, 3):
                volume = root / f"6347.part{index}.rar"
                volume.write_bytes(b"fixture")
                volumes.append(volume)
            app = make_app(self.module)
            app.initial_input_files = {path.resolve() for path in volumes}
            app.cleanup_extracted_results(root)
            self.assertTrue(all(path.exists() for path in volumes))

    def test_zip_based_document_and_app_containers_are_not_expanded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = make_app(self.module)
            for filename in ("游戏目录.xlsx", "game.apk"):
                path = root / filename
                path.write_bytes(b"PK\x03\x04fixture")
                self.assertIsNone(app.is_archive_file(path), filename)


if __name__ == "__main__":
    unittest.main(verbosity=2)

