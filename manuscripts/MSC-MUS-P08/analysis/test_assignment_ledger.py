import tempfile,unittest,random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from assignment_ledger import allocate,ledger,reconcile,withdraw
from inference import analyze
from export_schema import read_export
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
        export=self.path.with_suffix(".csv")
        data.drop(columns="withdrawn").to_csv(export,index=False)
        restored=read_export(export,empirical=True)
        self.assertEqual(reconcile(self.path,restored),80)
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

    def test_strict_export_tokens_and_leading_zeroes(self):
        for i in range(80):
            allocate(self.path,f"{i:032x}",i%2,"0"*63+"1",
                     eligible=True,consented=True,baseline_complete=True,rng=random.Random(i))
        records=pd.DataFrame(ledger(self.path)).drop(columns="withdrawn")
        scores=fixture().iloc[:80].drop(columns=["participant_id","training","authority","manual"]).reset_index(drop=True)
        data=pd.concat([records,scores],axis=1)
        data["heard_version"]=data.heard_version.astype("object")
        data.loc[0,"heard_version"]="false"
        data.loc[1,"heard_version"]="NA"
        data.loc[2,"heard_version"]="true"
        path=self.path.with_suffix(".csv")
        data.to_csv(path,index=False)
        frame=read_export(path,empirical=True)
        self.assertEqual(reconcile(self.path,frame),80)
        self.assertEqual(frame.participant_id.iloc[0],"0"*32)
        self.assertEqual(frame.bank_digest.iloc[0],"0"*63+"1")
        self.assertTrue(frame.system_schedule.str.len().eq(4).all())
        self.assertFalse(frame.heard_version.iloc[0])
        self.assertTrue(pd.isna(frame.heard_version.iloc[1]))
        self.assertTrue(frame.heard_version.iloc[2])
        result=analyze(frame)
        self.assertFalse(result["full_cohort_target_defined"])
        self.assertEqual(result["secondary_holm"],{"H2":None,"H3":None})
        for token in ("0","yes","FALSE","null"," "):
            bad=data.copy();bad.loc[0,"heard_version"]=token
            bad.to_csv(path,index=False)
            with self.assertRaises(ValueError):read_export(path,empirical=True)
        for bad in (data.assign(withdrawn=0),data.drop(columns="bank_digest"),
                    data.assign(system_schedule="12"),data.assign(schema_version="wrong")):
            bad.to_csv(path,index=False)
            with self.assertRaises(ValueError):read_export(path,empirical=True)
        data.to_csv(path,index=False)
        text=path.read_text()
        path.write_text(text.replace("participant_id,","participant_id,participant_id,",1))
        with self.assertRaisesRegex(ValueError,"duplicate CSV fields"):read_export(path,empirical=True)
