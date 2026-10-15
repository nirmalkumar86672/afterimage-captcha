import time,unittest
import server
class VerificationTests(unittest.TestCase):
 def setUp(self):
  server.CHALLENGES.clear()
  server.CHALLENGES['test']={'answer':'star','expires':time.monotonic()+30,'used':False}
 def test_correct_answer_and_replay(self):
  self.assertEqual(server.verify('test','star'),(200,{'success':True}))
  self.assertEqual(server.verify('test','star')[0],409)
 def test_normalization(self):
  self.assertEqual(server.verify('test',' STAR '),(200,{'success':True}))
 def test_wrong_answer_consumes_challenge(self):
  self.assertEqual(server.verify('test','moon'),(200,{'success':False}))
  self.assertEqual(server.verify('test','star')[0],409)
 def test_expired(self):
  server.CHALLENGES['test']['expires']=0
  self.assertEqual(server.verify('test','star')[0],410)
 def test_public_metadata(self):
  data=server.new_challenge()
  self.assertNotIn('answer',data)
  self.assertEqual((data['width'],data['height']),(384,240))
if __name__=='__main__':unittest.main()
