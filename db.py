#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Database handling
"""

import sqlite3 as lite
import process_files
from config import config
import json
import os
from unidecode import unidecode
import re


"""
15 most common words in english, french, and spanish.
"""
COMMON_WORDS = {'english' : set(['the', 'of', 'and', 'to', 'in', 'a', 'that', 'for', 'is', 'as',
                                 'was', 'by', 'on', 'it', 'with']),
                'spanish' : set(['de', 'la', 'en', 'y', 'el', 'los', 'que', 'a', 'las', 'del',
                                 'para', 'un', 'se', 'una', 'por']),
                'french' : set(['de', 'la', 'des', 'et', 'les', 'à', 'le', 'en', 'du', 'dans',
                                '«', 'une', 'par', 'sur', 'au'])}

def store_uploaded_files(orig, tran, erase_and_upload):
    """
    Receives data from uploaded files and stores them in the /texts directory. If the files
    are already there and the user decides to upload anyway, the files are erased and reuploaded.
    If they had been stored in the database already, they are erased from the database to
    be processed again.
    =Parameters=
    orig: Tuple containing orig_upload, orig_lang, orig_name, and orig_text.
    tran: Tuple containing tran_upload, tran_lang, tran_name, and tran_text.
    erase_and_upload: 'false' if it is the first attempt. 'true' if the files are already stored
    and the user wants to reupload them.
    """
    orig_upload, orig_lang, orig_name, orig_ext = orig
    tran_upload, tran_lang, tran_name, tran_ext = tran
    erase_and_upload = erase_and_upload
    
    texts_path = config.TEXTS_PATH

    if len(os.listdir(texts_path)) == 0 or os.listdir(texts_path) == ['.DS_Store'] or os.listdir(texts_path) == ['.DS_Store','._.DS_Store']:
        orig_save_path = texts_path + "/" + '_'.join(["1", orig_name, orig_lang, "original"]) + orig_ext
        tran_save_path = texts_path + "/" + '_'.join(["1", tran_name, tran_lang, "translation"]) + tran_ext
        orig_upload.save(orig_save_path)
        tran_upload.save(tran_save_path)
        create_para_db_and_processed_docs_table() #Create paragraphs.db for the first time.
        create_words_db_and_processed_docs_table() #Create words.db for the first time.
        return json.dumps({'status':'OK',
                           'user_prompt':'Do you want to upload more files?'})
    else:
        if erase_and_upload == 'false':
            for filename in os.listdir(texts_path):
                if filename.split('_')[1] == orig_name or filename.split('_')[1] == tran_name:
                    return json.dumps({'status':'files already in database',
                                       'user_prompt': "These files are already stored in the database! Do you want to reupload them?"})
            nums_taken = set()
            for filename in os.listdir(texts_path):
                if filename != '.DS_Store' or filename != '._.DS_Store':
                    try:
                        nums_taken.add(int(filename.split("_")[0]))
                    except Exception:
                        continue
            missing_num = None
            for idx in range(1, len(os.listdir(texts_path))/2+1):
                if idx not in nums_taken:
                    missing_num = str(idx)
                    break
            if missing_num:
                new_num = missing_num
            else:    
                new_num = str(int(len(os.listdir(texts_path))/2) + 1)
            orig_save_path = texts_path + "/" + '_'.join([new_num, orig_name, orig_lang, "original"]) + orig_ext
            tran_save_path = texts_path + "/" + '_'.join([new_num, tran_name, tran_lang, "translation"]) + tran_ext
            orig_upload.save(orig_save_path)
            tran_upload.save(tran_save_path)
            return json.dumps({'status':'OK',
                           'user_prompt':'Do you want to upload more files?'})
        else:
            new_num = None
            for filename in os.listdir(texts_path):
                if filename.split('_')[1] == orig_name or filename.split('_')[1] == tran_name:
                    new_num = filename.split('_')[0]
                    os.remove(texts_path + "/" + filename)
                    table_name = "[" + '_'.join(filename.split(".")) + "]"
                    erase_table_and_words_for_doc(table_name)
            orig_save_path = texts_path + "/" + '_'.join([new_num, orig_name, orig_lang, "original"]) + orig_ext
            tran_save_path = texts_path + "/" + '_'.join([new_num, tran_name, tran_lang, "translation"]) + tran_ext
            orig_upload.save(orig_save_path)
            tran_upload.save(tran_save_path)
            return json.dumps({'status':'OK',
                           'user_prompt':'Do you want to upload more files?'})
    
def create_para_db_and_processed_docs_table():
    """
    Creates for the first time paragraphs.db and a table to store a list of the docs
    that have already been processed and uploaded to the database.
    """
    if os.path.isfile(config.PARA_DB):
        os.remove(config.PARA_DB)
        
    try:
        con = lite.connect(config.PARA_DB)
        cur = con.cursor()
        cur.execute("CREATE TABLE processed_docs(Filename TEXT)")
        con.commit()
    except lite.Error:
        if con:
            con.rollback()
#        print("Error: {}".format(e.args[0]))
    finally:
        if con:
            con.close()
    return

def create_words_db_and_processed_docs_table():
    """
    Creates for the first time words.db and a table to store a list of the docs
    that have already been processed and uploaded to the database.
    """
    if os.path.isfile(config.WORDS_DB):
        os.remove(config.WORDS_DB)
        
    try:
        con = lite.connect(config.WORDS_DB)
        cur = con.cursor()
        cur.execute("CREATE TABLE processed_docs(Filename TEXT)")
        for lang in ['sp', 'fr', 'en']:
            for letter in ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r',
                           's','t','u','v','w','x','y','z']:
                table_name = lang+'_'+letter
                cur.execute("CREATE TABLE {}(Word TEXT, Document TEXT, Paragraph INT)".format(table_name))
                #Create index to search for translations
                search_index_name = table_name + "_search_idx"
                cur.execute("CREATE INDEX {} ON {} (Word, Document, Paragraph)".format(search_index_name, table_name))
                #Create index to erase all the words that came from a document.
                erase_index_name = table_name + "_erase_idx"
                cur.execute("CREATE INDEX {} ON {} (Document)".format(erase_index_name, table_name))
        con.commit()
    except lite.Error:
        if con:
            con.rollback()
#        print("Error: {}".format(e.args[0]))
    finally:
        if con:
            con.close()
    return

def erase_table_and_words_for_doc(table_name):
    """
    Erase table_name from processed docs, erase its paragraphs table, and erase all the words
    that came from that document.
    =Args=
        table_name: Name of the document to erase in the format [#_docName_language_ext].
    """
    try:
        con = lite.connect(config.PARA_DB)
        cur = con.cursor()
        cur.execute("DELETE FROM processed_docs WHERE Filename=?", (table_name,))
        cur.execute("DROP TABLE IF EXISTS {}".format(table_name))
        con.commit()
    except lite.Error:
        if con:
            con.rollback()
#        print("Error: {}".format(e.args[0]))
        if con:
            con.close()
    
    lang_abb = table_name.split('_')[2][:2]
    try:
        con = lite.connect(config.WORDS_DB)
        cur = con.cursor()
        for letter in ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r',
                           's','t','u','v','w','x','y','z']:
            words_table_name = lang_abb + '_' + letter
            cur.execute("DELETE FROM {} WHERE Document=?".format(words_table_name), (table_name,))
        cur.execute("DELETE FROM processed_docs WHERE Filename=?", (table_name,))
        con.commit()
    except lite.Error:
        if con:
            con.rollback()
#        print("Error: {}".format(e.args[0]))
    finally:
        if con:
            con.close()
    
    return

def erase_files(docs_to_erase):
    """
    Erase all data related to the docs in docs_to_erase.
    =Args=
        docs_to_erase: List of docs to erase.
    """
    try:
        docs = []
        for pair_docs in docs_to_erase:
            doc1, doc2 = pair_docs.split("?")
            doc1 = doc1.strip()
            doc2 = doc2.strip()
            docs.append(doc1)
            docs.append(doc2)
        
        file_names = []
        table_names = []
        for doc in docs:
            num, rest = doc.split(":")
            name, lang, origin, ext = rest.split("/")
            name = name.strip()
            name = '-'.join(name.split(' '))
            lang = lang.strip()
            origin = origin.strip()
            ext = ext.strip()
            file_name = "_".join([num, name, lang, origin])+"."+ext
            file_names.append(file_name)
            
            table_name = "[" + "_".join([num, name, lang, origin, ext]) + "]"
            table_names.append(table_name)
        
        for filename in file_names:
            os.remove(config.TEXTS_PATH + "/" + filename)
            
        for table in table_names:
            erase_table_and_words_for_doc(table)
    except Exception as e:
        return {'status':'error', 'user_prompt':str(e)}
        
    return {'status':'ok'}
    

class ModelStatus():
    """
    Enum class to keep track of Model's state.
    """
    def __init__(self):
        self.NULL = 0
        self.CREATED = 1
        self.PROCESSING = 2
        self.DONE = 3        

class StoreInDb():
    """
    Class that handles the processing of files in the /texts folder and the uploading to the
    database of such file.
    """
    def __init__(self, path=''):
        
        # Path where the progress of processing is stored for visualization
        if path == '':
            self.path = 'docs_storage'
        else:
            self.path = path
        # Docs that need to be processed
        self.docs_to_process = []
        # How many docs need to be processed in total
        self.length_of_docs_to_process = 0
        # Docs that have already been processed
        self.processed_docs = []
        # Doc that is currently being processed
        self.doc_in_process = ''
        # Current process in progress
        self.current_process = ''
        # Status of the model
        self.model_status = ModelStatus()
        self.status = self.model_status.CREATED
    
    def get_paragraphs_from_doc(self, file_path):
        """
        Takes a file_path, process the file, and returns a tuple with the paragraphs from that file and
        the name of the table to store the data into, in this format: #_fileName_language_fileType.
        =Parameters=
        file_path: Path of the file to be uploaded to the database. Must be a docx or pdf.
        """
        assert isinstance(file_path, str), "Sorry, but the file_path is not a string!"
        assert file_path.endswith('.docx') or file_path.endswith('.pdf'), "Sorry, but this is not a docx or pdf file!."
        
        name_of_table, type_of_file = file_path.split(".")
        name_of_table = "[" + name_of_table + "_" + type_of_file + "]"
        real_path_to_file = config.TEXTS_PATH + '/' + file_path
        
        if type_of_file == 'docx':
            status = process_files.docx_to_text(real_path_to_file)
            if status['status'] == 'ok':
                paragraphs = status['data']
            else:
                return status
            status = process_files.docx_to_text(real_path_to_file, footnotes=True)
            if status['status'] == 'ok':
                footnotes = status['data']
            else:
                return status
            para_norep, foot_norep = process_files.norep_text_and_footnotes(paragraphs, footnotes)
            para_join = process_files.join_paragraphs(para_norep)
            foot_join = process_files.join_paragraphs(foot_norep)
            
        else:
            pdf_text = process_files.pdf_to_text(real_path_to_file)
            try:
                pdf_text = json.loads(pdf_text)
                status = pdf_text['status']
                if status == 'EXTRACTION_ERROR':
                    return pdf_text
            except Exception:
                paragraphs, footnotes = process_files.split_pdf_by_paragraphs(pdf_text)
                para_norep, foot_norep = process_files.norep_text_and_footnotes(paragraphs, footnotes)
                para_join = process_files.join_paragraphs(para_norep)
                foot_join = process_files.join_paragraphs(foot_norep)
            
        return {'status':'ok', 'data': (name_of_table, para_join, foot_join)}
     
    def create_table_for_doc(self, name_of_table, paragraphs, footnotes):
        """
        Takes a tuple of tuples of paragraphs and uploads the data to the database. It 
        creates a new table named #_fileName_language_fileType, in which each paragraph of the
        file is stored in a different row.
        =Parameters=
        name_of_table: The name of the new table in the format #_fileName_language.
        paragraphs: Tuple of paragraphs to upload to the new table.
        """
        assert len(name_of_table) > 0, "The name of the table's string is empty!"
        assert len(paragraphs) > 0, "Your tuple of paragraphs is empty!"
        
        try:
            con = lite.connect(config.PARA_DB)
            
            cur = con.cursor()
            
            cur.execute("DROP TABLE IF EXISTS {}".format(name_of_table))
            cur.execute("CREATE TABLE {}(Paragraph TEXT)".format(name_of_table))
            if len(paragraphs) > 0:
                cur.executemany("INSERT INTO {} VALUES(?)".format(name_of_table), paragraphs)
            if len(footnotes) > 0:
                cur.executemany("INSERT INTO {} VALUES(?)".format(name_of_table), footnotes)
            
            cur.execute("INSERT INTO processed_docs(Filename) VALUES(?)", (name_of_table,))
            
            con.commit()
    
            
        except lite.Error:
            
            if con:
                con.rollback()
                
#            print("Error: {}".format(e.args[0]))
            
        finally:
            
            if con:
                con.close()
                
        return
                
    def search_docs_in_processed_docs(self):
        """
        Searches processed_docs table and the /text folder and returns a list of the docs that
        are in /texts that have not been processed and therefore have not been uploaded to the
        processed_docs table.
        """
        texts_path = config.TEXTS_PATH
        files_in_texts_folder = [filename for filename in os.listdir(texts_path)]
        
        try:
            con = lite.connect(config.PARA_DB)
            cur = con.cursor()
            
            cur.execute("SELECT Filename FROM processed_docs")
            docs_in_db = cur.fetchall()
            processed_docs = [doc[0].split("_")[1] for doc in docs_in_db]
            docs_to_process = [filename for filename in files_in_texts_folder\
                               if filename.split("_")[1] not in processed_docs]
            docs_to_process = [filename for filename in docs_to_process\
                               if filename.endswith('.docx') or filename.endswith('.pdf')]
            return docs_to_process
        except lite.Error:
            if con:
                con.rollback()
#            print("Error: {}".format(e.args[0]))
            docs_to_process = []
            return docs_to_process
        finally:
            if con:
                con.close()
        
        return
            

    def fill_words_db(self, doc):
        """
        Fill words.db with all the words extracted from "doc".
        =Args=
            doc: Name of doc to divide into words.
        """
    
        id_words = {'a' : set(), 'b' : set(), 'c' : set(), 'd' : set(), 'e' : set(), 'f' : set(),
                    'g' : set(), 'h' : set(), 'i' : set(), 'j' : set(), 'k' : set(), 'l' : set(), 
                    'm' : set(), 'n' : set(), 'o' : set(), 'p' : set(), 'q' : set(), 'r' : set(), 
                    's' : set(), 't' : set(), 'u' : set(), 'v' : set(), 'w' : set(), 'x' : set(), 
                    'y' : set(), 'z' : set()}
        
        doc = '_'.join(doc.split('.'))
        lang = doc.split('_')[2]
        abb = lang[:2]
        doc_table_name = "[" + doc + "]"
        
        try:
            con = lite.connect(config.PARA_DB)
            cur = con.cursor()
            cur.execute("SELECT rowid, Paragraph FROM {}".format(doc_table_name.encode('utf-8')))
            para_in_doc = cur.fetchall()
            con.close()
        
        except lite.Error:
                if con:
                    con.rollback()
#                print("Error: {}".format(e.args[0]))
                if con:
                    con.close()
        
        for p in para_in_doc:
            id_ = p[0]
            words = p[1].lower().strip()
            words = re.sub(r'[¡!@#$%^&*()={}|\\/.,¿?~><:;«÷≥≤0-9§"\'\[\]¨¨+`´Çç]', '', words)
            words = words.replace(u'\u201c', '').replace(u'\u201d', '')
            for w in words.split(' '):
                w = w.strip()
                if w.endswith(u'\u2019') or w.startswith(u'\u2019'):
                    w = w.replace(u'\u2019', '')
                if w not in COMMON_WORDS[lang]:
                    if len(w) > 2:
                        if unidecode(w[0]) == '-':
                            continue
                        try:
                            id_words[unidecode(w[0])].add((w, doc_table_name, id_))
                        except Exception:
                            try:
                                id_words[unidecode(w[1])].add(w[1:], doc_table_name, id_)
                            except:
                                continue
                    
        try:
            con = lite.connect(config.WORDS_DB)
            cur = con.cursor()
            for letter, words in id_words.items():
                if len(words) > 0:
                    table_name = abb + "_" + letter
                    cur.executemany("INSERT INTO {} VALUES(?, ?, ?)".format(table_name), tuple(id_words[letter]))
            cur.execute("INSERT INTO processed_docs VALUES(?)", (doc_table_name,))
            con.commit()
            con.close()
            
        except lite.Error:
                if con:
                    con.rollback()
#                print("Error: {}".format(e.args[0]))
                if con:
                    con.close()

    def store_new_docs_in_db(self):
        """
        Takes all the documents in the /texts folder that haven't been processed and saved; it
        then process them and stores them in the database.
        """
        self.status = self.model_status.PROCESSING
        self.docs_to_process = self.search_docs_in_processed_docs()
        self.length_of_docs_to_process = len(self.docs_to_process)
        if self.length_of_docs_to_process <= 0:
            return json.dumps({'status':'ERROR','user_prompt':'There are no documents to process'}) 
        for doc in list(self.docs_to_process):
            self.doc_in_process = doc
            self.current_process = 'Getting paragraphs and footnotes from {}.'.format(self.doc_in_process)
            paragraphs_from_doc_status = self.get_paragraphs_from_doc(doc)
            if paragraphs_from_doc_status['status'] == 'ok':
                name_of_table, paragraphs, footnotes = paragraphs_from_doc_status['data']
            else:
                os.remove(config.TEXTS_PATH + "/" + self.doc_in_process)
                for doc in self.processed_docs:
                    rest, ext = doc.split(".")
                    table_name = "[" + rest + "_" + ext + "]"
                    erase_table_and_words_for_doc(table_name)
                    os.remove(config.TEXTS_PATH + "/" + doc)
                return paragraphs_from_doc_status
            self.current_process = 'Storing paragraphs and footnotes in database.'
            self.create_table_for_doc(name_of_table, paragraphs, footnotes)
            self.current_process = 'Storing words in database'
            self.fill_words_db(doc)
            self.processed_docs.append(doc)
            self.docs_to_process.remove(doc)
        self.status = self.model_status.DONE
        
        return {'status':'ok', 'user_prompt':''}

    
def get_processed_files():
    """
    Get a list with all the processed documents to put it in a dropdown menu in translate.html
    """
    processed_docs = []
    try:
        con = lite.connect(config.PARA_DB)
        cur = con.cursor()
        cur.execute("SELECT * FROM processed_docs")
        processed_docs = cur.fetchall()
        con.close()
    except lite.Error:
#        print("Error: {}".format(e.args[0]))
        if con:
            con.rollback()
            con.close()
                    
    list_of_docs = []
    orig_doc = None
    tran_doc = None
    for idx in range(0, len(processed_docs), 2):
        num1, name1, language1, origin1, ext1 = processed_docs[idx][0].split("_")
        num1 = num1[1:]
        name1 = ' '.join(name1.split('-'))
        ext1 = ext1[:-1]
        new_doc1 = num1 + ": " + name1 + " / " + language1 + " / " + origin1 + " / " + ext1
        
        num2, name2, language2, origin2, ext2 = processed_docs[idx+1][0].split("_")
        num2 = num2[1:]
        name2 = ' '.join(name2.split('-'))
        ext2 = ext2[:-1]
        new_doc2 = num2 + ": " + name2 + " / " + language2 + " / " + origin2 + " / " + ext2
        
        if origin1 == "original":
            orig_doc = new_doc1
            tran_doc = new_doc2
        else:
            orig_doc = new_doc2
            tran_doc = new_doc1
        
        list_of_docs.append(orig_doc)
        list_of_docs.append(tran_doc)
        
    return list_of_docs
        
    
    
    
    
    
    
    
    
