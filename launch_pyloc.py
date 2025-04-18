#! /usr/bin/env python

__author__ = 'iped'
import os


from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt'

# If linux, set the QT_QPA_PLATFORM environment variable to xcb
if os.name == 'posix':
    if 'QT_QPA_PLATFORM' not in os.environ:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'

from view.pyloc import PylocControl
import yaml

if __name__ == '__main__':
    config = None
    with open(os.path.join(os.path.dirname(__file__), 'config.yml')) as f:
        config = yaml.safe_load(f)
    controller = PylocControl(config)
    controller.exec_()
