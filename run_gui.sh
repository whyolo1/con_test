#!/bin/bash
conda activate controller-map
export PYTHONPATH=src
python3 -m controller_mapper gui
if [ $? -ne 0 ]; then
    read -p "Press Enter to exit..."
fi
