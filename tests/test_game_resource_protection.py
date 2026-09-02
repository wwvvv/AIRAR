from pathlib import Path
import importlib.util, tempfile
p=Path('src/airar.py'); s=importlib.util.spec_from_file_location('airar',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
class R:
 def after(self,d,cb,*a): cb(*a)
class V:
 def set(self,x): pass
a=m.SmartUnpackerGUI.__new__(m.SmartUnpackerGUI); a.root=R(); a.stats={'archives_found':0}; a.stats_vars={}; a.update_stats=lambda:None
with tempfile.TemporaryDirectory() as td:
 root=Path(td)
 for name in ['auto-1-LT1.save','persistent','archive.rpa','script.rpyc']:
  f=root/name; f.write_bytes(b'PK\x03\x04game-save-data')
  assert a.is_archive_file(f) is None, f'{name} was misdetected as archive'
 print('game_resource_protection=OK')

