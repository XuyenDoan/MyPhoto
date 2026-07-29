# Bundled models

## face_detector.onnx

**Ultra-Light-Fast-Generic-Face-Detector-1MB** (`version-RFB-320.onnx`),
by [Linzaer](https://github.com/Linzaer/Ultra-Light-Fast-Generic-Face-Detector-1MB),
MIT License. Used by `myphoto.preset_engine.face_detector` to give
`preset_engine.auto_suggest` a real (deep-learning) face-presence signal —
replacing an earlier hue-range "does this look like skin color" heuristic,
which had no way to distinguish a real face from any other object that
happens to share a similar hue/saturation range, and was unreliable across
different skin tones.

Runs fully offline via `onnxruntime` (CPU) — no network call, no per-image
cost, no photo ever leaves the device.

```
MIT License

Copyright (c) 2019 linzai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
