import unittest
from falcon_engine import FalconEngine
import os

class TestFalconEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FalconEngine()

    def test_variable_assignment(self):
        # Testing basic secure let
        code = "secure let x = 100"
        self.engine.tokenize(code)
        self.engine.execute(0, len(self.engine.tokens))
        self.assertEqual(self.engine.variables.get('x'), 100)

    def test_math_operations(self):
        # Testing falcon.math (10 + 20)
        code = "secure let result = 10 + 20"
        self.engine.tokenize(code)
        self.engine.execute(0, len(self.engine.tokens))
        self.assertEqual(self.engine.variables.get('result'), 30)

    def test_loop_logic(self):
        # Testing if the engine handles repeat blocks without crashing
        code = "repeat 2\nprint(\"test\")\nendrepeat"
        try:
            self.engine.tokenize(code)
            self.engine.execute(0, len(self.engine.tokens))
            success = True
        except:
            success = False
        self.assertTrue(success)

if __name__ == '__main__':
    unittest.main()
  
