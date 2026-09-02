from pathlib import Path
import tempfile, importlib.util
spec=importlib.util.spec_from_file_location('airar',Path('src/airar.py')); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class Root:
 def after(self,d,cb,*a): cb(*a)
a=m.SmartUnpackerGUI.__new__(m.SmartUnpackerGUI); a.root=Root(); a.log_message=lambda x:None
a.settings={'ad_rules':['广告*','*.url']}; a.last_output_dir=None
with tempfile.TemporaryDirectory() as td:
 p=Path(td); dest=p/'current'; root=p/'work'; game=root/'Bodysmith Tales'; game.mkdir(parents=True); dest.mkdir()
 (game/'game.exe').write_bytes(b'MZ'); (game/'data.bin').write_bytes(b'x'); (root/'release.apk').write_bytes(b'PK'); (root/'广告说明.txt').write_text('x'); (root/'readme.txt').write_text('delete')
 a.destination_dir=dest; a.session_extract_roots={root}; a.organize_game_outputs()
 assert (dest/'Bodysmith Tales'/'game.exe').exists(); assert (dest/'release.apk').exists(); assert not root.exists(); assert not any(x.name=='readme.txt' for x in dest.rglob('*'))
 print('organizer=OK game=OK apk=OK ads_removed=OK leftovers_removed=OK')

