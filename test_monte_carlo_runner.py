"""Offline regression tests for launcher orchestration (no expensive simulation)."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import monte_carlo_runner as m

class Plans(unittest.TestCase):
    def test_all_plans(self):
        for profile in m.PROFILES:
            for study in m.STUDIES:
                tasks=m.load_plan(study,profile)
                self.assertEqual(bool(tasks),study!="P02")
                self.assertFalse(any(t.r for t in tasks))
        tasks=m.load_plan("P09","full")
        self.assertEqual(len([t for t in tasks if t.name.startswith("ipw/") and t.name.endswith("/aggregate")]),40)
        self.assertEqual(len([t for t in tasks if t.name.startswith("paired/") and t.name.endswith("/aggregate")]),9)
        chosen=m.selected(tasks,"ipw/cell-06/aggregate")
        self.assertEqual(len(chosen),101)
        self.assertEqual(len(chosen[-1].deps),100)
        self.assertEqual(len([t for t in m.load_plan("P05","full") if t.name.endswith("/aggregate")]),19)
    def test_dependency_failure_transitive(self):
        jobs=[m.job("one","x.py"),m.job("two","x.py",deps=["one"]),
              m.job("three","x.py",deps=["two"]),m.job("other","x.py")]
        def worker(t):
            if t.name=="one":raise RuntimeError("deliberate test failure")
            return "EXECUTED"
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            result=m.schedule(jobs,worker,2)
        self.assertEqual(result,{"one":"FAILED","two":"BLOCKED","three":"BLOCKED","other":"EXECUTED"})

class Execution(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.analysis=self.root/"manuscripts"/"MSC-MUS-P01"/"analysis"
        self.analysis.mkdir(parents=True)
        self.out=self.root/"build"/"test"
        self.out.mkdir(parents=True)
        (self.analysis/"toy.py").write_text('import json; print(json.dumps({"value": 2}))\n')
        self.patcher=patch.object(m,"ROOT",self.root)
        self.patcher.start();self.addCleanup(self.patcher.stop)
        self.ctx={"head":"test-head","sources":{"source":"test-hash"},"environment":{"python":"test"}}
    def execute(self,job):
        with patch.object(m,"git",return_value="test-head"),patch.object(m,"source_hash",return_value=self.ctx["sources"]):
            return m.execute(job,self.ctx,self.out,"P01",1)
    def test_execute_resume_corruption_and_dependency_digest(self):
        task=m.job("group/shard-00000","toy.py")
        self.assertEqual(self.execute(task),"EXECUTED")
        self.assertEqual(self.execute(task),"REUSED")
        self.assertEqual([x.name for x in (self.out/"group").glob("shard-*.json")],["shard-00000.json"])
        dep=m.job("group/aggregate","toy.py",deps=[task.name])
        self.assertEqual(self.execute(dep),"EXECUTED")
        self.assertEqual(self.execute(dep),"REUSED")
        m.output(self.out,task.name).write_text('{"value":3}')
        self.assertFalse(m.reusable(task,self.ctx,self.out))
        self.assertFalse(m.reusable(dep,self.ctx,self.out))
        self.assertEqual(self.execute(task),"EXECUTED")
        self.assertTrue(m.reusable(dep,self.ctx,self.out))
    def test_invalid_json_and_failed_exit(self):
        for text in ('print("NaN")','raise SystemExit(2)'):
            (self.analysis/"toy.py").write_text(text)
            task=m.job("bad","toy.py")
            with self.assertRaises((RuntimeError,ValueError)):self.execute(task)
            self.assertFalse(m.output(self.out,"bad").exists())
            self.assertFalse(m.stamp(self.out,"bad").exists())
    def test_lock(self):
        with m.lock(self.out):
            with self.assertRaises(ValueError):
                with m.lock(self.out):pass
        self.assertFalse((self.out/".run.lock").exists())

if __name__=="__main__":unittest.main()
