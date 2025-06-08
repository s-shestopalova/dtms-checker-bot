#!/bin/bash
apt-get update && apt-get install -y wget unzip chromium chromium-driver
pip install -r requirements.txt
