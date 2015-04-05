@echo off
echo Converting file to .wav: %1
ffmpeg -i %1 %1.wav