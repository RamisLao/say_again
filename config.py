#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Config
"""
import os

class Config():
    """
    Static global class holding important parameters.
    """
    ROOT_PATH = os.path.dirname(os.path.realpath(__file__)) #Path to project's directory
    STATIC_PATH = os.path.dirname(os.path.realpath(__file__)) + '/static' #Path to static resources
    TEXTS_PATH = os.path.dirname(os.path.realpath(__file__)) + '/texts' #Path to text resources
    if not os.path.exists(TEXTS_PATH):
        os.makedirs(TEXTS_PATH)
    DATABASE_PATH = os.path.dirname(os.path.realpath(__file__)) + '/databases'
    if not os.path.exists(DATABASE_PATH):
        os.makedirs(DATABASE_PATH)
    PARA_DB = DATABASE_PATH + '/paragraphs.db'
    WORDS_DB = DATABASE_PATH + '/words.db'
    
global config
config = Config()

