# $Id: TestScanFiles.py 34 2008-01-08 15:21:57Z graham $
#
# Unit testing for WebBrick library functions (Functions.py)
# See http://pyunit.sourceforge.net/pyunit.html
#

import sys
import unittest
import re
from os.path import normpath

sys.path.append("../..")
from MiscLib.ScanFiles import *

class TestScanFiles(unittest.TestCase):
    def setUp(self):
        self.testpath = "resources/"
        self.testpatt = re.compile( r'^TestScanFiles.*\.txt$' )
        return

    def tearDown(self):
        return

    # Actual tests follow

    def testCollectShallow(self):
        files    = CollectFiles(self.testpath,self.testpatt,recursive=False)
        expected = [ (self.testpath,"TestScanFiles1.txt")
                   , (self.testpath,"TestScanFiles2.txt")
                   ]
        assert files == expected, "Wrong file list: "+repr(files)

    def testCollectRecursive(self):
        files    = CollectFiles(self.testpath,self.testpatt)
        expected = [ (self.testpath,"TestScanFiles1.txt")
                   , (self.testpath,"TestScanFiles2.txt")
                   , (self.testpath+"TestScanFilesSubDir","TestScanFiles31.txt")
                   , (self.testpath+"TestScanFilesSubDir","TestScanFiles32.txt")
                   ]
        assert files == expected, "Wrong file list: "+repr(files)

    def testJoinDirName(self):
        # normpath used here to take care of dir separator issues.
        n = joinDirName("/root/sub","name")
        assert n==normpath("/root/sub/name"), "JoinDirName failed: "+n
        n = joinDirName("/root/sub/","name")
        assert n==normpath("/root/sub/name"), "JoinDirName failed: "+n
        n = joinDirName("/root/sub/","/name")
        assert n==normpath("/name"), "JoinDirName failed: "+n

    def testReadDirNameFile(self):
        assert readDirNameFile(self.testpath,"TestScanFiles1.txt"), "Read dir,file 'TestScanFiles1.txt' failed"

    def testReadFile(self):
        assert readFile(self.testpath+"TestScanFiles1.txt"), "Read file 'TestScanFiles1.txt' failed"


# Code to run unit tests directly from command line.
# Constructing the suite manually allows control over the order of tests.
def getTestSuite():
    suite = unittest.TestSuite()
    suite.addTest(TestScanFiles("testCollectShallow"))
    suite.addTest(TestScanFiles("testCollectRecursive"))
    suite.addTest(TestScanFiles("testJoinDirName"))
    suite.addTest(TestScanFiles("testReadDirNameFile"))
    suite.addTest(TestScanFiles("testReadFile"))
    return suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(getTestSuite())
    