from django.test import TestCase

from django.core.files.base import ContentFile

from django.contrib.auth.models import User

import os
from os import path

from utils import rand_string
from models import upload_storage as fs
from models import Attachment, UploadedFile, RepositoryFile, _repos_dir

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
    
class AttachmentTestCase(TestCase):
    
    def test(self):
        a = Attachment()
        a.clean()
        a.save()
        
        self.assertEqual(a.detailed_instance(), a)

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
            name = filename,
        )
        a.uploaded_file.save(filename, ContentFile(contents))
        a.clean()
        a.save()

        # TODO self.assertEqual(a.url,?)
        # TODO self.assertEqual(a.path,?)
        self.assertEqual(a.detailed_instance(), a)
        self.assertEqual(a.attachment_ptr.__class__, Attachment)
        self.assertNotEqual(a.attachment_ptr.__class__, UploadedFile)
        self.assertEqual(a.attachment_ptr.detailed_instance(), a)
        self.assertEqual(a.attachment_ptr.detailed_instance().__class__, UploadedFile)

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
                
                # TODO self.assertEqual(a.url,?)
                
            finally:
                fh.close()
                os.remove(f_path)
        finally:
            os.rmdir(r_path)

        self.assertEqual(a.detailed_instance(), a)
        self.assertEqual(a.attachment_ptr.__class__, Attachment)
        self.assertNotEqual(a.attachment_ptr.__class__, RepositoryFile)
        self.assertEqual(a.attachment_ptr.detailed_instance(), a)
        self.assertEqual(a.attachment_ptr.detailed_instance().__class__, RepositoryFile)

