# -*- mode: python -*-

block_cipher = None


a = Analysis(['pySRD9c.py'],
             pathex=['C:\\'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='pySRD9c.self_test',
          debug=False,
          strip=False,
          upx=True,
          console=True , version='pySRD9c.version.txt', icon='pySRD9c.ico')
