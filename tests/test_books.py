import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["BOOKS_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import books

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = books.db()
        for f in Path(__file__).resolve().parent.parent.joinpath("library").glob("*_sample.txt"):
            books.ingest_file(cls.con, f)
    def test_topics_cross_source(self):
        terms = [t for t, _, _ in books.discover_topics(self.con, 20)]
        self.assertIn("alienation", terms)
    def test_contrast_needs_two_sources(self):
        by, _, _ = books.contrast(self.con, "alienation")
        self.assertIsNotNone(by); self.assertEqual(len(by), 2)
        none, _, _ = books.contrast(self.con, "zeppelin")
        self.assertIsNone(none)
    def test_audit_flags_bad_answers(self):
        ex = Path(__file__).resolve().parent.parent / "examples"
        ids = [r["id"] for r in self.con.execute("SELECT id FROM chunks ORDER BY id")]
        good = (ex / "good_answer.txt").read_text().replace("[p1]", f"[p{ids[0]}]").replace("[p2]", f"[p{ids[1]}]")
        r = books.audit_answer(self.con, good)
        self.assertEqual(r["unresolved"], [])
        bad = books.audit_answer(self.con, (ex / "bad_answer.txt").read_text())
        self.assertEqual(bad["verdict"], "CONDITIONAL")
        self.assertIn(99, bad["unresolved"])
        self.assertTrue(bad["uncited"])

if __name__ == "__main__":
    unittest.main()
