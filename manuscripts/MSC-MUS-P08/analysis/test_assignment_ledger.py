import tempfile,unittest,random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from assignment_ledger import allocate,ledger,reconcile,withdraw
from inference import analyze
from test_inference import fixture

class LedgerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"p08.sqlite"
    def assign(self,i,**kw):
        args=dict(eligible=True,consented=True,baseline_complete=True,rng=random.Random(i))
        args.update(kw)
        return allocate(self.path,f"{i:032x}",i%2,"a"*64,**args)
    def test_retry_concurrency_and_gates(self):
        with self.assertRaises(ValueError):self.assign(0,consented=False)
        self.assertFalse(self.path.exists())
        with ThreadPoolExecutor(max_workers=8) as pool:
            same=list(pool.map(self.assign,[1]*16))
            list(pool.map(self.assign,range(2,34)))
        self.assertTrue(all(x==same[0] for x in same))
        self.assertEqual(len(ledger(self.path)),33)
        self.assertNotIn("slot",same[0])
        self.assertNotIn("sequence",same[0])
        with self.assertRaises(ValueError):
            allocate(self.path,"0"*32,0,"b"*64,eligible=True,consented=True,baseline_complete=True)
    def test_reconcile_and_model(self):
        for i in range(80):self.assign(i)
        data=pd.DataFrame(ledger(self.path))
        f=fixture().iloc[:80].drop(columns=["participant_id","training","authority","manual"]).reset_index(drop=True)
        data=pd.concat([data,f],axis=1)
        data.loc[0,"ownership1"]=None
        self.assertEqual(reconcile(self.path,data),80)
        self.assertEqual(analyze(data)["randomised"],80)
        for k,v in [("authority",2),("manual",2),("training",2),("bank_digest","b"*64),
                    ("system_schedule","9999"),("schema_version","bad"),("randomised_at","2020-01-01T00:00:00Z")]:
            bad=data.copy();bad.loc[0,k]=v
            with self.assertRaises(ValueError):reconcile(self.path,bad)
        for bad in (data.iloc[1:],pd.concat([data,data.iloc[:1]]),data.assign(participant_id="extra")):
            with self.assertRaises(ValueError):reconcile(self.path,bad)
    def test_withdrawal(self):
        self.assign(1);data=pd.DataFrame(ledger(self.path))
        withdraw(self.path,f"{1:032x}");withdraw(self.path,f"{1:032x}")
        with self.assertRaises(ValueError):self.assign(1)
        with self.assertRaises(ValueError):reconcile(self.path,data)
