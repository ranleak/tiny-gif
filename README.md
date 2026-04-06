# TinyGIF
Make GIF files smaller using Python.

## Install Requirements
If you want to use the simple TinyGIF, install the requirements with:
```
pip install -r requirements.txt
```

If you want to use the smart TinyGIF (better when you want to make un-optimized files smaller without reducing the resolution) install the requirements like for the simple one, and then install numpy with:
```
pip install numpy
```

## Regular Mode
Regular TinyGIF has the standard features for a GIF compressor. It runs very well on pretty much any CPU, from 2 core to 64 core!

## Smart Mode
Smart mode is better when you don't want to lower the resolution of an un-optimized GIF. It lowers file size by removing redundant pixel changes. This uses a Computer Vision/Heuristic Delta algorithm.