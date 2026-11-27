import random
import tempfile
import unittest
from pathlib import Path

from allocation import allocate
from task import evaluate_stage, system_choices


class TestP08Task(unittest.TestCase):
    def test_allocated_authority_and_execution_crossed(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "test.sqlite"
            rng = random.Random(17)
            assignments = {tuple(allocate(ledger, str(i), 0, rng).values())
                           for i in range(12)}
        self.assertEqual(assignments, {(0, 0), (0, 1), (1, 0), (1, 1)})
        for authority, manual in assignments:
            for index, rule in enumerate(system_choices(3)):
                with self.subTest(authority=authority, manual=manual, stage=index):
                    preference = 1 - rule
                    outcome = evaluate_stage(authority, manual, rule, preference,
                                             5. if manual else None)
                    self.assertEqual(outcome.selected, preference if authority else rule)
                    self.assertEqual(outcome.applied, outcome.selected)

    def test_missing_manual_confirmation_preserves_previous_version(self):
        result = evaluate_stage(1, 1, 0, 1, None)
        self.assertEqual(result.selected, 1)
        self.assertIsNone(result.applied)
        for seconds in (-1, 11, float("nan")):
            with self.assertRaises(ValueError):
                evaluate_stage(1, 1, 0, 1, seconds)

    def test_balanced_rule_family(self):
        schedules = [system_choices(i) for i in range(16)]
        self.assertEqual(len(set(schedules)), 16)
        self.assertEqual([sum(stage) for stage in zip(*schedules)], [8] * 4)

    def test_all_revision_paths_resolve_to_unique_auditable_audio(self):
        import hashlib
        import wave

        from fixture_audio import DURATION, RATE, generate

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            manifest = generate(folder)
            self.assertEqual(len({record["sha256"] for record in manifest["files"]}), 16)
            for record in manifest["files"]:
                path = folder / record["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])
                with wave.open(str(path), "rb") as audio:
                    self.assertEqual(audio.getnframes(), RATE * DURATION)
                    self.assertEqual(audio.getframerate(), RATE)
