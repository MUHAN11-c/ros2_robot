import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/'examples/offline_labs'
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class OfflineLabs(unittest.TestCase):
    def test_plan_contract(self):
        validate=module('plan_contract').validate
        self.assertEqual(validate('[{"skill":"navigate","place":"desk","timeout":60}]')[0]['skill'],'navigate')
        for item in [dict(skill=[],place='desk',timeout=10),dict(skill='navigate',place={},timeout=10),dict(skill='navigate',place='desk',timeout=True),dict(skill='navigate',place='desk',timeout=float('nan')),dict(skill='shell',command='x',timeout=10)]:
            with self.assertRaises(ValueError):validate(json.dumps([item]))
    def test_policy_output_limits_and_staleness(self):
        gate=module('policy_gate').gate
        self.assertEqual(gate([5.]*6,[0.]*6,.02,.02),[.01]*6)
        self.assertIsNone(gate([5.]*6,[0.]*6,.11,.02))
        self.assertIsNone(gate([5.]*6,[0.]*6,-.01,.02))
        with self.assertRaises(ValueError):gate([float('nan')]*6,[0.]*6,.02,.02)
        with self.assertRaises(ValueError):gate([0.]*5,[0.]*6,.02,.02)
    def test_manifest_change_detection(self):
        manifest=module('dataset_manifest').manifest
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'input.csv';p.write_text('t,q\n0,.1\n')
            first=manifest(folder)
            self.assertEqual(first,manifest(folder))
            p.write_text('t,q\n0,.2\n')
            self.assertNotEqual(first['files'][0]['sha256'],manifest(folder)['files'][0]['sha256'])
            (Path(folder)/'link').symlink_to(p)
            with self.assertRaises(ValueError):manifest(folder)
    def test_policy_search_reproducible_improvement(self):
        evaluate=module('rl_gain_search').evaluate
        baseline=evaluate(0.,range(100,110))
        candidate=evaluate(2.,range(100,110))
        self.assertEqual(candidate,evaluate(2.,range(100,110)))
        self.assertGreater(candidate['mean_return'],baseline['mean_return'])
        self.assertLess(candidate['mean_final_error'],baseline['mean_final_error'])

if __name__=='__main__':unittest.main(verbosity=2)
