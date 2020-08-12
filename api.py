#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
API
"""

import json
import os
import db
from db import StoreInDb
from translate import SearchAndTranslate
import re

def make_register():
  """ Creates a dict registry object to hold all annotated definitions.
  Returns: A dictionary with all definitions in this file.
  """
  registry = {}
  def registrar(func):
      registry[func.__name__] = func
      return func
  registrar.all = registry
  return registrar
  
# Dictionary holding all definitions in this file.
endpoint = make_register()

@endpoint
def upload_files(args, files):
    """
    Takes the files uploaded through the app and stores it in the /texts directory.
    =Parameters=
    args: Dictionary with keys 'endpoint', 'orig_lang', 'tran_lang', and 'erase_and_upload'
    files: Dictionary wth keys 'orig_upload' and 'tran_upload'.
    """
    if 'orig_upload' not in files:
        return json.dumps({'status':'ERROR',
                          'user_prompt':"Original document not specified. Choose a file to upload."})
    if 'tran_upload' not in files:
        return json.dumps({'status':'ERROR',
                          'user_prompt':"Translated document not specified. Choose a file to upload."})
    orig_upload = files['orig_upload']
    if not orig_upload:
        return json.dumps({'status':'ERROR',
                          'user_prompt':"Original file not valid. Choose a valid file to upload."})
    tran_upload = files['tran_upload']
    if not tran_upload:
        return json.dumps({'status':'ERROR',
                          'user_prompt':"Translated file not valid. Choose a valid file to upload."})
    
    orig_upload_name = orig_upload.filename
    tran_upload_name = tran_upload.filename
    
    orig_no_periods = re.sub(r'\.', '-', orig_upload_name[:-5]) + orig_upload_name[-5:]
    tran_no_periods = re.sub(r'\.', '-', tran_upload_name[:-5]) + tran_upload_name[-5:]

    orig_no_hyphens = re.sub(r'_', '-', orig_no_periods)
    tran_no_hyphens = re.sub(r'_', '-', tran_no_periods)
    
    orig_no_double_hyphens = re.sub(r'--', '-', orig_no_hyphens)
    tran_no_double_hyphens = re.sub(r'--', '-', tran_no_hyphens)
    
    orig_name, orig_ext = orig_no_double_hyphens.split('.')
    orig_ext = '.' + orig_ext
    if orig_ext != '.docx' and orig_ext != '.pdf':
        return json.dumps({'status':'ERROR',
                          'user_prompt':"Original document is not a docx or pdf! Choose valid file."})
    tran_name, tran_ext = tran_no_double_hyphens.split('.')
    tran_ext = '.' + tran_ext
    if tran_ext != '.docx' and tran_ext != '.pdf':
        return json.dumps({'status':'ERROR',
                          'user_prompt':"Translated document is not a docx or pdf! Choose valid file."})
    
    if orig_name == tran_name:
        return json.dumps({'status':'ERROR',
                           'user_prompt':'Your files have the same name. Choose valid files!'})
    
    orig_lang = args['orig_lang']
    tran_lang = args['tran_lang']
    if orig_lang == tran_lang:
        return json.dumps({'status':'ERROR',
                           'user_prompt':'You chose the same language for both documents!'})
    
    orig = (orig_upload, orig_lang, orig_name, orig_ext)
    tran = (tran_upload, tran_lang, tran_name, tran_ext)
    erase_and_upload = args['erase_and_upload']
    
    response = db.store_uploaded_files(orig, tran, erase_and_upload)        
    
    return response

@endpoint
def check_if_there_are_docs_to_process(args, files):
    """
    Checks if there are docs to process and returns a message for index.html, to know
    if index.html should disable or not the button-process-docs.
    """
    store_in_db = StoreInDb()
    docs_to_process = store_in_db.search_docs_in_processed_docs()
    if len(docs_to_process) > 0:
        return json.dumps({'status':'there are docs to process'})
    else:
        return json.dumps({'status':'all docs are processed'})
    

@endpoint
def save_new_docs_to_db(args, files):
    """
    Takes the documents that are already stored in /texts and that are not in the database,
    process them and uploads them to the database so that they are ready to be searched.
    """
    processing_model = StoreInDb()
    try:
        status = processing_model.store_new_docs_in_db()
        return json.dumps(status)
    except Exception as e:
        return json.dumps({'status':'error', 'user_prompt' : str(e)})

@endpoint
def translate_text(args, files): #Add 
    """
    Takes a phrase sent by the user and returns the paragraphs where it appears and their 
    translations.
    =Args=
        args: Dictionary with keys 'text_to_translate', 'orig_lang', 'tran_lang',
              'limit_of_search', and 'select_doc'.
    """
    phrase = args['text_to_translate']
    if not phrase:
        return json.dumps({'status' : 'error', 'user_prompt': 'No text was sent for translation!'})
    
    orig_lang = args['orig_lang']
    tran_lang = args['tran_lang']
    if orig_lang == tran_lang:
        return json.dumps({'status': 'error', 'user_prompt': 'Original language and translation language are the same!'})
    limit_of_search = args['limit_of_search']
    select_doc = args['select_doc']
    
    if select_doc == 'All':
        select_doc = None
    else:
        if select_doc.split('/')[1].strip() != orig_lang:
            return json.dumps({'status':'error', 'user_prompt':'Original language and selected file do not match!'})
        
    if not limit_of_search:
        limit_of_search = None
    else:
        try:
            limit_of_search = int(limit_of_search)
        except Exception:
            return json.dumps({'status' : 'error', 'user_prompt' : '"How many results do you want" must be an integer!'})
    if limit_of_search == 0:
        return json.dumps({'status':'error', 'user_prompt':'You asked for 0 results!'})
    
    try:
        main_word = args['main_word']
    except:
        main_word = None
        
    translate_object = SearchAndTranslate(phrase, orig_lang, tran_lang, limit_of_search, main_word, select_doc)
    final_json = translate_object.ask_for_translation()
    return json.dumps(final_json)
    
@endpoint
def get_processed_files(args, files):
    """
    Get a list with all the processed documents to put it in a dropdown menu in translate.html
    """
    processed_files = db.get_processed_files()
    if processed_files:
        return json.dumps({'status':'ok',"processed_files" : processed_files})
    else:
        return json.dumps({'status':'error',"processed_files" : "none"})
    
@endpoint
def erase_files(args, files):
    """
    Erase files, paragraphs' table, and words for the files in args['docs_to_erase']
    =Args=
        docs_to_erase: all the documents that we want to erase
    """
    if len(args) == 1:
        return json.dumps({'status':'error', 'user_prompt':'No files selected!'})
    
    docs_to_erase = []
    for name, value in args.items():
        if name != 'endpoint':
            docs_to_erase.append(value)

    if not docs_to_erase:
        return json.dumps({'status':'error', 'user_prompt':'There are no files to erase!'})
    status = db.erase_files(docs_to_erase)
    if status['status'] == 'ok':
        return json.dumps({'status':'ok', 'user_prompt':''})
    else:
        return json.dumps(status)

def resolve_endpoint(endpoint_str, args, files):
  """ Reroutes the request to the matching endpoint definition. 
  See make_registrar for more information.
  Params: arguments and files needed to run the endpoint (every endpoint receives both dictionaries). Also receives the
  name of the endpoint.
  Returns: The output of the endpoint.
  """
  if endpoint_str in endpoint.all:
      return endpoint.all[endpoint_str](args, files)
  else:
      return 'No such endpoint %s' % endpoint_str
