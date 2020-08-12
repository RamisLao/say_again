#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Read and process docx
"""

from cStringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
try:
    from xml.etree.cElementTree import XML
except ImportError:
    from xml.etree.ElementTree import XML
import zipfile
import json

WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PARA = WORD_NAMESPACE + 'p'
TEXT = WORD_NAMESPACE + 't'

def docx_to_text(path, footnotes=False):
    """
    Unzips a docx file and returns either the document text separated by paragraphs or
    the footnotes separated in paragraphs.
    =Parameters=
    path: Path of the docx file to unzip.
    footnotes: If False, the document text is extracted; if True, the footnotes are extracted.
    """
    assert path.endswith('.docx'), "This is not a .docx file!"
    try:
        document = zipfile.ZipFile(path)
        if footnotes == False:
            xml_content = document.read('word/document.xml')
        else:
            xml_content = document.read('word/footnotes.xml')
        document.close()
    except Exception:
        if footnotes == False:
            return {'status':'EXTRACTION_ERROR',
                    'user_prompt': 'There was an error while unzipping the docx! Maybe your docx has a defect, but you can try again.'}
        else:
            return {'status':'ok', 'data': []}
    
    tree = XML(xml_content)
    
    paragraphs = []
    for paragraph in tree.getiterator(PARA):
        texts = [node.text for node in paragraph.getiterator(TEXT) if node.text]
        if texts:
            texts = ''.join(texts)
            if len(texts.split(" ")) > 1:
                if type(texts) == str:
                    texts = texts.decode('utf-8')
                paragraphs.append(texts)
            
    return {'status':'ok', 'data': paragraphs}


def pdf_to_text(file_path, pages=None):
    """
    Takes a pdf file, reads it, and returns a Unicode string with the text in the file.
    =Parameters=
    file_path: The path of the pdf file that you want to read.
    pages: A list with the pages that you want to read from the pdf file. Defaults to None (Read all pages).
    """
    assert file_path.endswith('.pdf'), "This is not a pdf file!"
    
    if not pages:
        pagenums = set()
    else:
        pagenums = set(pages)

    try:
        output = StringIO()
        manager = PDFResourceManager()
        laparams = LAParams()
        laparams.all_texts = True
        converter = TextConverter(manager, output, laparams=laparams)
        interpreter = PDFPageInterpreter(manager, converter)
    except Exception:
        return json.dumps({'status':'EXTRACTION_ERROR',
                           'user_prompt': 'There was a problem initializing PDF Miner!'})

    try:
        with open(file_path, 'rb') as f:
            for page in PDFPage.get_pages(f, pagenums):
                interpreter.process_page(page)
    except Exception:
        return json.dumps({'status':'EXTRACTION_ERROR',
                           'user_prompt':"There was an error while opening the pdf file. The file could be encrypted. A solution could be to open it, export it as another PDF file, and upload the new file that was generated."})
            
    converter.close()
    text = output.getvalue()
    output.close
    return text.decode('utf-8')

def split_pdf_by_paragraphs(pdf_text):
    """
    Takes string extracted from a pdf and returns a list for main paragraphs and for
    footnotes, where each row is a paragraph in the text.
    =Parameters=
    pdf_text = String extracted from a pdf file.
    """
    paragraphs = pdf_text.split('\n\n')
    clean_paragraphs = []
    clean_footnotes = []
        
    for para in paragraphs:
        split_n = para.split('\n')
        join_n = ''.join(split_n)
        no_space = " ".join(join_n.split()) #Removes all white spaces at the beginning, middle or end
        if len(no_space.split(" ")) > 1:
            
            try:
                _ = float(no_space.split(" ")[0])
                split_hyph = no_space.split('-')
                join_hyph = ''.join(split_hyph)
                clean_footnotes.append(join_hyph)
                continue
            except Exception:
                pass

            split_hyph = no_space.split('-')
            join_hyph = ''.join(split_hyph)
            clean_paragraphs.append(join_hyph)
            
    return clean_paragraphs, clean_footnotes

def norep_text_and_footnotes(text, footnotes):
    """
    Takes text and footnotes extracted from a doc and process them. Erases repetitions from both.
    =Parameters=
    text: Text from doc.
    footnotes: Footnotes from doc.
    """
    chapters = []
    
    text_no_rep = []
    for para in text:
        if para not in text_no_rep:
            try:
                chapter, _ = para.split(" ")[:-1], int(para.split(" ")[-1])
                if chapter not in chapters:
                    text_no_rep.append(para)
                    chapters.append(chapter)
                continue
            except Exception:
                pass
            text_no_rep.append(para)
            
    footnotes_no_rep = []
    for foot in footnotes:
        if foot not in footnotes_no_rep:
            try:
                _, chapter = int(foot.split(" ")[0]), foot.split(" ")[1:]
                if chapter not in chapters:
                    footnotes_no_rep.append(foot)
                    chapters.append(chapter)
                continue
            except Exception:
                pass
            footnotes_no_rep.append(foot)
    
    return text_no_rep, footnotes_no_rep

def join_paragraphs(text):
    """
    Takes either the paragraphs or footnotes of a doc and merges the ones that have been
    separated by mistake. When a paragraph doesn't end with a period, and the next one starts
    with lowercase, they are joined. Returns a tuple of tuples.
    =Parameters=
    text: List of paragraphs to process.
    """
    joined_text = []
    ignore = False
    
    for idx in range(len(text)-1):
        if not ignore:
            if text[idx][-1] != '.' and text[idx+1][0].islower():
                joined_text.append((text[idx]+' '+text[idx+1],))
                ignore = True
            else:
                joined_text.append((text[idx],))
        else:
            ignore = False
            
    return tuple(joined_text)













