"""Public CLI and grammar checks for variant 20."""
import subprocess
import sys
import unittest
from pathlib import Path
import yaml
from translator import SyntaxProblem, translate


class TranslatorTests(unittest.TestCase):
    def test_all_constructions(self):
        content="var BASE +001.25\nvar DELTA -0.125\nvar A { ^[BASE]. { ^[DELTA]. 0.0. }. }\n{ ^[A]. { }. }"
        self.assertEqual(yaml.safe_load(translate(content)), [[1.25,[-0.125,0.0]],[]])
        self.assertEqual(yaml.safe_load(translate("1.2 -3.4")), [1.2,-3.4])

    def test_bad_tokens_delimiter_name_and_scope(self):
        for bad in ("{1.2}", "{ 1.2. ", "^[LATE] var LATE 1.0", "var lowercase 1.0",
                    "var A 1.0 var A 2.0", "{ 1. }", "^A", "^[ABSENT]"):
            with self.subTest(bad=bad), self.assertRaisesRegex(SyntaxProblem,r"\d+:\d+:"):
                translate(bad)

    def test_examples_through_cli(self):
        folder=Path(__file__).resolve().parent
        for name,want in (("warehouse",[[4.5,12.0],[0.75,5.0]]),("climate",[[18.0,22.5],[-2.0,0.5]])):
            done=subprocess.run([sys.executable,str(folder/"translator.py"),"--input",
                                 str(folder/"examples"/f"{name}.cfg")],capture_output=True,text=True,check=True)
            self.assertEqual(yaml.safe_load(done.stdout),want)
        failure=subprocess.run([sys.executable,str(folder/"translator.py"),"--input",
                                str(folder/"examples"/"bad.cfg")],capture_output=True,text=True)
        self.assertEqual(failure.returncode,1)
        self.assertEqual(failure.stdout,"")
        self.assertIn("1:",failure.stderr)


if __name__=="__main__":
    unittest.main(verbosity=2)
