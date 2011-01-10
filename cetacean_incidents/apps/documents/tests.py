from django.test import TestCase

from django.conf import settings
from django.core.files.base import ContentFile

from django.db import transaction

from django.contrib.auth.models import User

import os
from os import path

from utils import rand_string
from models import upload_storage as fs
from models import _repos_url, _repos_dir
from models import DocumentType, Document, UploadedFile, RepositoryFile

class UploadTestCase(TestCase):
    def test_fs(self):
        test_filename = 'test-' + rand_string()
        
        contents = 'contestns'
        
        fs.save(test_filename, ContentFile(contents))
        self.assertEqual(fs.exists(test_filename), True)
        self.assertEqual(fs.size(test_filename), len(contents))
        self.assertEqual(fs.open(test_filename).read(), contents)
        
        fs.delete(test_filename)
        self.assertEqual(fs.exists(test_filename), False)
    
class DocumentTestCase(TestCase):
    
    def test(self):
        a = Document()
        a.clean()
        a.save()
        
        self.assertEqual(a.specific_instance(), a)

class UploadedFileTestCase(TestCase):

    def setUp(self):
        self.test_user = User.objects.create(
            username='test_user',
        )

    def test(self):
        filename = 'up-' + rand_string()
        contents = 'upladded contestsn'
    
        a = UploadedFile(
            uploader = self.test_user,
        )
        a.uploaded_file.save(filename, ContentFile(contents))
        a.clean()
        a.save()

        # TODO self.assertEqual(a.url,?)
        # TODO self.assertEqual(a.path,?)

        self.assertEqual(a.specific_instance(), a)
        self.assertEqual(a.document_ptr.__class__, Document)
        self.assertNotEqual(a.document_ptr.__class__, UploadedFile)
        self.assertEqual(a.document_ptr.specific_instance(), a)
        self.assertEqual(a.document_ptr.specific_instance().__class__, UploadedFile)
    
    def test_transmute(self):
        
        doctype = DocumentType.objects.create(name='transmuted')
        doc = Document(
            document_type = doctype,
        )
        doc.save()
        uf = UploadedFile.transmute_document(
            doc,
            uploader=self.test_user,
        )
        uf.save()
        self.assertEqual(uf.document_ptr_id, doc.id)
        self.assertEqual(uf.document_ptr, doc)
        self.assertEqual(uf.document_type, doc.document_type)
        self.assertEqual(doc.uploadedfile, uf)
        
        self.assertRaises(ValueError, UploadedFile.transmute_document, doc, uploader=self.test_user)

class RepositoryFileTestCase(TestCase):

    def test(self):
        r = 'test-repo-' + rand_string()
        r_path = path.join(_repos_dir, r)
        f = 'rep-' + rand_string()
        f_path = path.join(r_path, f)
        c = 'contentsts'
        
        os.mkdir(r_path)
        try:
            fh = open(f_path, 'wb')
            try:
                fh.write(c)
                a = RepositoryFile(repo=r, repo_path=f)
                a.clean()
                a.save()
                
                self.assertEqual(a.path, path.join(_repos_dir, r, f))
                self.assertEqual(a.url, _repos_url + r + '/' + f)
                
            finally:
                fh.close()
                os.remove(f_path)
        finally:
            os.rmdir(r_path)

        self.assertEqual(a.specific_instance(), a)
        self.assertEqual(a.document_ptr.__class__, Document)
        self.assertNotEqual(a.document_ptr.__class__, RepositoryFile)
        self.assertEqual(a.document_ptr.specific_instance(), a)
        self.assertEqual(a.document_ptr.specific_instance().__class__, RepositoryFile)

