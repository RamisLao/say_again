#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Translate text
"""
from unidecode import unidecode
import sqlite3 as lite
from config import config
from googletrans import Translator
import re
from collections import OrderedDict
from db import get_processed_files

class SearchAndTranslate():
    """
    Class that searches a word in the db and returns all possible translations.
    """
    def __init__(self, phrase, orig_lang, tran_lang, limit_of_search, main_word, select_doc):
        
        #Limit of search
        self.limit_of_search = limit_of_search
        #Phrase that the user wants to translate
        self.phrase = unicode(phrase, 'utf-8')
        #Phrase separated by words, converted into lowercase and reverse sorted
        self.phrase_list = self.phrase.lower().split()
        self.phrase_list_reversed = sorted(self.phrase_list, key=lambda x: len(unidecode(x)), reverse=True)
        if main_word:
            self.main_word = unicode(main_word.lower(), 'utf-8')
            self.phrase_list_reversed.remove(self.main_word)
            self.phrase_list_reversed.insert(0, self.main_word)
        #Original languange
        self.orig_lang = orig_lang
        #Translation language
        self.tran_lang = tran_lang
        #Paragraphs to translate
        self.orig_paragraphs = None
        #Docs and paragraphs to search
        self.docs_and_paragraphs = None
        self.translated_doc = None
        self.translated_paragraphs = None
        #Original paragraphs and translated paragraphs
        self.orig_and_tran_paragraphs = None
        #Search only inside this file
        if select_doc:
            num_name, lang, origin, ext = select_doc.split('/')
            lang = lang.strip()
            origin = origin.strip()
            ext = ext.strip()
            num, name = num_name.split(':')
            name = name.strip()
            name = '-'.join(name.split(' '))
            complete_doc = '_'.join([num, name, lang, origin, ext])
            new_select_doc = "[" + complete_doc + "]"
            self.select_doc = new_select_doc
        else:
            self.select_doc = select_doc

    def sort_orig_paragraphs(self):
        """
        Sort self.orig_paragraphs in order of importance. First put the paragraphs where the whole
        self.phrase is found, and then put the paragraphs where self.phrase is found incomplete.
        """
        order_of_paragraphs = {}
        
        for number in range(len(self.phrase_list)+1):
            order_of_paragraphs[number] = []
        
        low_and_joined_phrase = ''.join(self.phrase.split(' ')).lower()
        for paragraph in self.orig_paragraphs:
            doc, rowid, text = paragraph
            joined_text = ''.join(text[0].split(' ')).lower()
            if joined_text.find(low_and_joined_phrase) != -1:
                order_of_paragraphs[len(self.phrase_list)].append(paragraph)
            else:
                count = 0
                splitted_text = re.findall('\w+', unidecode(text[0]))
                for word in self.phrase.split(' '):
                    str_word = unidecode(word)
                    if str_word in splitted_text:
                        count += 1
                order_of_paragraphs[count].append(paragraph)
                
        order_dict = OrderedDict(sorted(order_of_paragraphs.items(), key=lambda x: x[0], reverse=True))
        new_list_of_paragraphs = []
        for key, value in order_dict.items():
            new_list_of_paragraphs += value
        self.orig_paragraphs = new_list_of_paragraphs
        
        return
        
    def search_word_in_db(self, list_of_words, select_doc):
        """
        Searches the word in the db and returns all the paragraphs where that word appears.
        =Args=
            list_of_words: List of the words found in self.phrase, sorted from longest word to 
                            shortest word.
        """
        orig_lang_abb = self.orig_lang[:2]
        
        for word in list_of_words:
            first_letter = word[0]
            name_of_table = orig_lang_abb + '_' + first_letter
    
            paragraphs_ids = []
            try:
                con = lite.connect(config.WORDS_DB)
                cur = con.cursor()
                if not select_doc:
                    cur.execute("SELECT * FROM {} WHERE Word=?".format(name_of_table), (word,))
                else:
                    cur.execute("SELECT * FROM {} WHERE Word=? AND Document=?".format(name_of_table), (word, select_doc))
                paragraphs_ids = cur.fetchall()
                con.close()
                
            except lite.Error:
                if con:
                    con.rollback()
#                print("Error: {}".format(e.args[0]))
                if con:
                    con.close()
            
            processed_files = get_processed_files()
            
            filtered_paragraphs_ids = []
            for id_ in paragraphs_ids:
                complete_name = id_[1]
                num1, name1, lang1, origin1, ext1 = complete_name.split("_")
                num1 = num1[1:]
                name1 = ' '.join(name1.split("-"))
                found_processed = (None, None)
                for processed in processed_files:
                    num2, rest = processed.split(":")
                    name2, lang2, origin2, ext2 = rest.split("/")
                    name2 = name2.strip()
                    lang2 = lang2.strip()
                    if num1 ==  num2 and name1 != name2:
                        found_processed = (processed, lang2)
                        break
                if found_processed[1] == self.tran_lang:
                    filtered_paragraphs_ids.append(id_)
                        
            paragraphs = []
            try:
                con = lite.connect(config.PARA_DB)
                cur = con.cursor()
                for para_id in filtered_paragraphs_ids:
                    cur.execute("SELECT Paragraph FROM {} WHERE rowid=?".format(para_id[1]), (para_id[2],))
                    paragraph = cur.fetchone()
                    paragraphs.append((para_id[1], para_id[2], paragraph))
                self.orig_paragraphs = paragraphs 
            except lite.Error:
                if con:
                    con.rollback()
#                print("Error: {}".format(e.args[0]))
                if con:
                    con.close()
            finally:
                if con:
                    con.close()
                    
            self.sort_orig_paragraphs()
            docs_and_paragraphs = self.get_paragraphs_from_translated_docs(self.orig_paragraphs)
            if docs_and_paragraphs:
                return docs_and_paragraphs
            else:
                continue
                
        return None
    
    def get_paragraphs_from_translated_docs(self, paragraphs):
        """
        Get the paragraphs of the documents that we are going to search, and return them in the
        form of a dictionary: {orig_doc : [tran_doc, paragraphs]}
        =Args=
            paragraphs: A list with all the paragraphs that will be translated. It is sorted by
                        importance. The paragraphs that contain all the main prhase come first,
                        and then come the paragraphs that contain less and less of the main phrase.
                        Each paragraph is a tuple with structure (doc, rowid, (text,)).
        """
      
        #Get the names of the original documents where the original paragraphs come from, and put
        #them in a set to avoid repetiton
        set_of_docs = set()
        for paragraph in paragraphs: #!!!Limit of search
            doc, _, _ = paragraph
            set_of_docs.add(doc)
            
        #Get all processed_docs and put them in a list
        try:
            con = lite.connect(config.PARA_DB)
            cur = con.cursor()
            cur.execute("SELECT * FROM processed_docs")
            processed_docs = cur.fetchall()
            con.close()
            
        except lite.Error:
            if con:
                con.rollback()
#            print("Error: {}".format(e.args[0]))
            if con:
                con.close()
                
        #Compare processed_docs to the set_of_docs to find the names of the translated documents
        #in which we are going to search for the translation
        #Store them in a dictionary with the form {orig_doc : (tran_doc, paragraphs)}
        docs_and_paragraphs = {}
        for doc_name in list(set_of_docs):
            doc_num = doc_name.split('_')[0][1:]
            for processed_doc in processed_docs:
                if processed_doc[0].split('_')[0][1:] == doc_num\
                and processed_doc[0] != doc_name\
                and processed_doc[0].split('_')[2] == self.tran_lang: #Do not add the documents that don't exist in the tran_lang that the user asked for
                    docs_and_paragraphs[doc_name] = [processed_doc[0], None]
        #Check if docs_and_paragraphs is empty.
        #If it is empty, then continue with next word.
        if len(docs_and_paragraphs) == 0:
            return None
                
        #Get all the paragraphs from the documents that we are going to search and put them inside
        #of the dictionary docs_and_paragraphs
        try:
            con = lite.connect(config.PARA_DB)
            cur = con.cursor()
            
            for doc_name, doc_to_extract in dict(docs_and_paragraphs).items():
                cur.execute("SELECT * FROM {}".format(doc_to_extract[0]))
                translated_paragraphs = cur.fetchall()
                docs_and_paragraphs[doc_name][1] = translated_paragraphs
            con.close()
                
        except lite.Error:
            if con:
                con.rollback()
#            print("Error: {}".format(e.args[0]))
            if con:
                con.close()
                
        return docs_and_paragraphs
    
    def find_translations(self, phrase_list, select_doc, limit_of_search=None):
                                             
        """
        Searches in the database for the paragraph that is the translation of the original one.
        =Args=
            paragraphs: A list with all the paragraphs that will be translated. It is sorted by
                        importance. The paragraphs that contain all the main prhase come first,
                        and then come the paragraphs that contain less and less of the main phrase.
                        Each paragraph is a tuple with structure (doc, rowid, (text,)).
        """
        import difflib
            
        orig_abb = self.orig_lang[:2]
        if orig_abb == 'sp':
            orig_abb = 'es'
        tran_abb = self.tran_lang[:2]
        if tran_abb == 'sp':
            tran_abb = 'es'
            
        self.docs_and_paragraphs = self.search_word_in_db(phrase_list, select_doc)
        if not self.docs_and_paragraphs:
            return {'status' : 'error', 'user_prompt':'No matches were found!'}
        
        """
        Recursive function to find translations.
        """
        def get_score(text1, text2):
            text2 = re.findall('\w+', text2)
            common_ratio = difflib.SequenceMatcher(None, text1, text2).ratio()
            return 100 * common_ratio
        
        def lower_bound(tran_text, len_paragraphs, lower_rowid, upper_rowid,
                        lower_not_found=False, upper_not_found=False):
            if lower_rowid >= 0:
                translated_paragraph = self.translated_paragraphs[lower_rowid][0]
                if get_score(tran_text, translated_paragraph) >= 25.:
                    return translated_paragraph, lower_rowid
                else:
                    found_paragraph, id_ = upper_bound(tran_text, len_paragraphs, lower_rowid,
                                                  upper_rowid + 1, lower_not_found=lower_not_found,
                                                  upper_not_found=upper_not_found)
                    return found_paragraph, id_
            elif lower_not_found and upper_not_found:
                return None, None
            else:
                lower_not_found = True
                found_paragraph, id_ = upper_bound(tran_text, len_paragraphs, lower_rowid,
                                              upper_rowid + 1, lower_not_found=lower_not_found,
                                              upper_not_found=upper_not_found)
                return found_paragraph, id_

                    
        def upper_bound(tran_text, len_paragraphs, lower_rowid, upper_rowid,
                        lower_not_found=False, upper_not_found=False):
            if upper_rowid < len_paragraphs:
                translated_paragraph = self.translated_paragraphs[upper_rowid][0]
                if get_score(tran_text, translated_paragraph) >= 25.:
                    return translated_paragraph, upper_rowid
                else:
                    found_paragraph, id_ = lower_bound(tran_text, len_paragraphs, lower_rowid - 1,
                                                  upper_rowid, lower_not_found=lower_not_found,
                                                  upper_not_found=upper_not_found)
                    return found_paragraph, id_
            elif lower_not_found and upper_not_found:
                return None, None
            else:
                upper_not_found = True
                found_paragraph, id_ = lower_bound(tran_text, len_paragraphs, lower_rowid - 1,
                                              upper_rowid, lower_not_found=lower_not_found,
                                              upper_not_found=upper_not_found)
                return found_paragraph, id_
        """
        End of recursive function.
        """
    
        translator = Translator()
    
        if limit_of_search == None:
            limit_of_search = len(self.orig_paragraphs)
    
        count = 0
        orig_and_tran_paragraphs = []
        for paragraph in self.orig_paragraphs: #!!!Limit of search!
            doc, rowid, text = paragraph
            lower_rowid = rowid - 1
            text = text[0]
            #Translated original text
            try:
                tran_text = translator.translate(text, dest=tran_abb, src=orig_abb).text
            except Exception:
                return {'status':'error', 'user_prompt':'You must be connected to the Internet!'}
            tran_text = re.findall('\w+', tran_text.lower())
            if len(tran_text) <= 25:
                text = "{ Caution! Due to the length of this paragraph, the translation might be wrong! } " + text
            #Paragraphs to look for
            self.translated_doc, self.translated_paragraphs = self.docs_and_paragraphs[doc]
            len_paragraphs = len(self.translated_paragraphs)
            if lower_rowid >= len_paragraphs:
                lower_rowid = int(len_paragraphs * .85)
            try:
                found_paragraph, id_ = lower_bound(tran_text, len_paragraphs, lower_rowid, lower_rowid)
            except RuntimeError:
                continue
                    
            if found_paragraph == None:
                continue
            second_id = id_ + 1
            _, name1, orig_lang, origin1, ext1 = doc.split("_")
            doc_name1 = "[" + name1 + "." + ext1
            _, name2, tran_lang, origin2, ext2 = self.translated_doc.split("_")
            doc_name2 = "[" + name2 + "." + ext2
            orig_and_tran_paragraphs.append({'item' : [{'doc' : doc_name1,
                                                        'lang' : orig_lang,
                                                        'orig_or_tran' : origin1,
                                                        '#p' : rowid,
                                                        'paragraph' : text},
                                                       {'doc' : doc_name2,
                                                        'lang' : tran_lang,
                                                        'orig_or_tran' : origin2,
                                                        '#p' : second_id,
                                                        'paragraph' : found_paragraph}]})
            count += 1
            if count >= limit_of_search:
                break
        self.orig_and_tran_paragraphs = orig_and_tran_paragraphs
        translated_phrase = translator.translate(self.phrase, dest=tran_abb, src=orig_abb).text
        
        return {'status' : 'ok', 'translated_phrase':translated_phrase}
            
    def return_search(self, translated_phrase):
        """
        Return a JSON with the schema:
            {
                'status' : 'text'
                'phrase' : 'text',
                'paragraphs' : [
                    {
                        'item' : [
                            {
                                'doc' : 'text',
                                'orig_lang' : 'text',
                                '#p' : 'int',
                                'paragraph' : 'text
                            },
                            {
                                'doc' : 'text',
                                'tran_lang' : 'text',
                                '#p' : 'int',
                                'paragraph' : 'text
                            }
                        ]
                    }
                ]
            }
        =Args=
            translated_phrase: Translated self.phrase to color it in the results.
        """
        if not self.orig_and_tran_paragraphs:
            return {'status':'error', 'user_prompt':'No matches were found!'}
        final_json = {'status' : 'ok',
                      'phrase' : self.phrase,
                      'translated_phrase': translated_phrase,
                      'main_word' : self.phrase_list_reversed[0],
                      'paragraphs' : self.orig_and_tran_paragraphs}
        
        return final_json
    def ask_for_translation(self):
        status = self.find_translations(self.phrase_list_reversed, self.select_doc, limit_of_search=self.limit_of_search)
        if status['status'] == 'ok':
            final_json = self.return_search(status['translated_phrase'])
            return final_json
        else:
            return status
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    