import importlib.util,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('validator',ROOT/'scripts/validate.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class PublishedChecks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  for f in ['README.md','eligibility-exclusions.json']:shutil.copy2(ROOT/f,self.root/f)
  for d in ['csv','lists']:shutil.copytree(ROOT/d,self.root/d)
 def tearDown(self):self.temp.cleanup()
 def test_current_artifact(self):self.assertEqual(v.validate(self.root)['roles'],65)
 def test_summary_drift_rejected(self):
  p=self.root/'README.md';p.write_text(p.read_text().replace('65 title-screened','66 title-screened'))
  with self.assertRaisesRegex(ValueError,'total'):v.validate(self.root)
 def test_missing_markdown_row_rejected(self):
  p=self.root/'lists/biostatistics.md';s=p.read_text();p.write_text('\n'.join(l for l in s.splitlines()if '/job/'not in l or '7086243d'not in l))
  with self.assertRaisesRegex(ValueError,'membership'):v.validate(self.root)
 def test_duplicate_csv_rejected(self):
  p=self.root/'csv/all.csv';s=p.read_text();p.write_text(s+s.splitlines()[1]+'\n')
  with self.assertRaisesRegex(ValueError,'duplicate'):v.validate(self.root)
 def test_confirmed_exclusion_rejected(self):
  p=self.root/'eligibility-exclusions.json';s=p.read_text().replace('fa9a0128-42c9-4f10-83a0-ce9bfb06ee17','2102b299-d56b-4050-8213-39a804d4f28d');p.write_text(s)
  with self.assertRaisesRegex(ValueError,'excluded'):v.validate(self.root)
 def test_surviving_referral_change_rejected(self):
  p=self.root/'README.md';baseline={'README.md':dict(v.markdown_links(p.read_text()))};p.write_text(p.read_text().replace('utm_campaign=comp-bio-all','utm_campaign=changed'))
  with self.assertRaisesRegex(ValueError,'surviving link'):v.validate(self.root,baseline)
 def test_year_boundary_interval(self):
  p=self.root/'README.md';s=p.read_text().replace('Snapshot 20 Oct 2026','Snapshot 03 Jan 2027').replace('18 have posting dates in the seven-day window ending 20 Oct 2026.','0 have posting dates in the seven-day window ending 03 Jan 2027.');p.write_text(s)
  self.assertEqual(v.validate(self.root)['roles'],65)
 def test_mismatched_interval_rejected(self):
  p=self.root/'README.md';p.write_text(p.read_text().replace('window ending 20 Oct 2026','window ending 19 Oct 2026'))
  with self.assertRaisesRegex(ValueError,'date interval'):v.validate(self.root)
if __name__=='__main__':unittest.main()
