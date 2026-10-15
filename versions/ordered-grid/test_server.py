import time,unittest
import server
class VerificationTests(unittest.TestCase):
 def setUp(self):
  server.CHALLENGES.clear()
  server.CHALLENGES['test']={'answer':['a','b','c'],'expires':time.monotonic()+30,'used':False}
 def test_correct_order_and_replay(self):
  self.assertEqual(server.verify('test',['a','b','c']),(200,{'success':True}))
  self.assertEqual(server.verify('test',['a','b','c'])[0],409)
 def test_wrong_order_consumes_challenge(self):
  self.assertEqual(server.verify('test',['c','b','a']),(200,{'success':False}))
  self.assertEqual(server.verify('test',['a','b','c'])[0],409)
 def test_expired_and_missing(self):
  server.CHALLENGES['test']['expires']=0
  self.assertEqual(server.verify('test',['a','b','c'])[0],410)
  self.assertEqual(server.verify('missing',[])[0],410)
 def test_public_options_do_not_disclose_order(self):
  data=server.new_challenge();entry=server.CHALLENGES[data['id']]
  self.assertNotIn('answer',data)
  self.assertEqual(len(data['options']),9)
  self.assertEqual(len(set(entry['answer'])),3)
  self.assertTrue(set(entry['answer']).issubset({o['id'] for o in data['options']}))
  self.assertTrue(entry['image'].startswith(b'\x89PNG'))
if __name__=='__main__':unittest.main()
