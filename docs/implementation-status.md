# Implementation status

## 0.2.0 local Bad Apple playback — 2026-09-20

Built-in Bad Apple playback uses package-relative vector data, not the original video path. Includes 6571 frames at 30 fps (219.033 seconds), 1–72 lines per frame, pause, five-second seek, restart and loop. No soundtrack; filled areas become outlines and black frames use the existing renderer's corner parking point. No firmware change.

Passed: 12 unit tests; source and frozen Tk/plugin self-tests; 36 playback sample positions; relocation from the ZIP into a new Unicode/space directory with fresh user data; six source/vector visual comparisons. Evidence lives in ignored `.gwflow/bad-apple/`, including `result.json`, `build.log`, `samples.png` and self-test reports. Release: `release/ScopeArcade-v0.2.0-Windows-x64.zip`.

Tools: standard CPython 3.13.7, PyInstaller 6.22.3, pySerial 3.5 and PyVISA 1.16.2. Offline conversion only: OpenCV headless 5.0.0.93 and NumPy 2.5.3; both excluded from runtime. Original MP4 and audio are excluded. Existing FTDI/VISA prerequisites apply to hardware use.

No packaging blocker remains. This change has no hardware writes; physical animation playback and Windows 10/another PC remain untested. The user explicitly requested local packaging without GitHub upload. Next executable step: extract the full ZIP, launch ScopeArcade.exe, select Bad Apple and click Start/Restart or computer preview. Online v0.1.0 remains unchanged.
