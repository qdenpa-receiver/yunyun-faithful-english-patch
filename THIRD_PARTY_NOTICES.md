# Third-Party Notices

Yunyun Faithful English Patch does not vendor third-party packages in the
source repository. Release executables are built with PyInstaller and may
include the Python runtime, the PyInstaller bootloader, and runtime Python
packages installed from PyPI for the patcher.

This notice is for third-party software used by the patching tool. It does
not identify or grant rights to any files from Yunyun Syndrome!? Rhythm
Psychosis, which are not redistributed by this project.

## Release Executable Components

| Component | License | Source |
| --- | --- | --- |
| Python runtime | Python Software Foundation License | https://www.python.org/ |
| PyInstaller bootloader | GPL-2.0-or-later with PyInstaller bootloader exception | https://pyinstaller.org/ |
| UnityPy | MIT | https://github.com/K0lb3/UnityPy |
| lz4 Python bindings | BSD License | https://github.com/python-lz4/python-lz4 |
| Brotli Python bindings | MIT | https://github.com/google/brotli |
| Pillow | PIL/Pillow MIT-CMU style license | https://github.com/python-pillow/Pillow |
| texture2ddecoder | MIT | https://github.com/K0lb3/texture2ddecoder |
| etcpak Python wrapper | MIT | https://github.com/K0lb3/etcpak |
| astc-encoder-py | MIT | https://github.com/K0lb3/astc-encoder-py |
| fmod_toolkit | MIT | https://github.com/K0lb3/fmod_toolkit |
| fsspec | BSD 3-Clause | https://github.com/fsspec/filesystem_spec |
| attrs | MIT | https://github.com/python-attrs/attrs |
| archspec | Apache-2.0 OR MIT | https://github.com/archspec/archspec |

The exact transitive dependency set can vary by Python, platform, and release
build environment. Before publishing a release artifact, verify the packaged
files and dependency metadata for that build.
