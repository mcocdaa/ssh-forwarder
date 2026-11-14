import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest


REPO_ROOT = Path(__file__).parents[1]


class ForwardingTest(unittest.TestCase):
    def _create_fake_systemctl(self, root: Path, log_path: Path):
        fake = root / "systemctl"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            "with open(os.environ['SYSTEMCTL_LOG'], 'a') as f:\n"
            "    f.write(' '.join(sys.argv[1:]) + '\\n')\n"
        )
        fake.chmod(0o755)
        return dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", SYSTEMCTL_LOG=str(log_path))

    def test_rules_reconnect_independently_and_stop_without_orphans(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(REPO_ROOT / "ssh-forward", root)
            (root / "forwards.conf").write_text(
                "SSH_HOST=user@first\n"
                "8100|coordinator|8000|control|0.0.0.0\n"
                "30080|inference|8000|inference\n"
                "SSH_HOST=user@second\n"
                "30084|127.0.0.1|8001|overseas|0.0.0.0\n"
            )
            log = root / "calls.jsonl"
            fake = root / "ssh"
            fake.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys, time\n"
                "with open(os.environ['FORWARD_TEST_LOG'], 'a') as f:\n"
                "    f.write(json.dumps({'pid': os.getpid(), 'args': sys.argv[1:]}) + '\\n')\n"
                "while True: time.sleep(1)\n"
            )
            fake.chmod(0o755)
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}", FORWARD_TEST_LOG=str(log))
            process = subprocess.Popen(
                ["bash", str(root / "ssh-forward"), "run"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
            )

            def calls():
                return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

            def wait_for(predicate):
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    if predicate():
                        return
                    time.sleep(0.05)
                self.fail("forwarder did not reach the expected state")

            try:
                wait_for(lambda: len(calls()) == 3)
                initial = calls()
                expected = {
                    ("user@first", "0.0.0.0:8100:coordinator:8000"),
                    ("user@first", "127.0.0.1:30080:inference:8000"),
                    ("user@second", "0.0.0.0:30084:127.0.0.1:8001"),
                }
                self.assertEqual({(c["args"][-1], c["args"][-2]) for c in initial}, expected)
                for call in initial:
                    self.assertEqual(call["args"].count("-L"), 1)
                    self.assertIn("ControlMaster=no", call["args"])
                    self.assertIn("ControlPath=none", call["args"])
                os.kill(initial[0]["pid"], signal.SIGTERM)
                wait_for(lambda: len(calls()) == 4)
                self.assertEqual(calls()[-1]["args"], initial[0]["args"])
                for call in initial[1:]:
                    os.kill(call["pid"], 0)
                process.terminate()
                _, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stderr.decode())
                for call in calls():
                    with self.assertRaises(ProcessLookupError):
                        os.kill(call["pid"], 0)
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate(timeout=5)

    def test_absent_forwards_conf_behaviors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(REPO_ROOT / "ssh-forward", root)
            conf = root / "forwards.conf"

            res_list = subprocess.run(
                ["bash", str(root / "ssh-forward"), "list"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(res_list.returncode, 0)
            self.assertIn("forwards.conf 未创建", res_list.stdout)

            res_del = subprocess.run(
                ["bash", str(root / "ssh-forward"), "del", "8080"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(res_del.returncode, 0)
            self.assertIn("forwards.conf 不存在", res_del.stdout)

            res_run = subprocess.run(
                ["bash", str(root / "ssh-forward"), "run"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(res_run.returncode, 0)
            self.assertIn("forwards.conf 不存在，跳过转发", res_run.stdout)

            res_add_no_host = subprocess.run(
                ["bash", str(root / "ssh-forward"), "add", "8080", "127.0.0.1", "80", "web"],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(res_add_no_host.returncode, 0)
            self.assertFalse(conf.exists())

    def test_add_del_validation_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(REPO_ROOT / "ssh-forward", root)
            conf = root / "forwards.conf"
            sys_log = root / "systemctl.log"
            env = self._create_fake_systemctl(root, sys_log)

            # Reject '|' in desc and whitespace in target host
            bad_desc = subprocess.run(
                ["bash", str(root / "ssh-forward"), "add", "--host", "u@h", "8080", "127.0.0.1", "80", "a|b"],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(bad_desc.returncode, 0)
            self.assertFalse(conf.exists())

            bad_host = subprocess.run(
                ["bash", str(root / "ssh-forward"), "add", "--host", "u@h", "8080", "127.0.0.1 bad", "80", "web"],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(bad_host.returncode, 0)
            self.assertFalse(conf.exists())

            # Existing conf without SSH_HOST= must reject add without --host
            conf.write_text("# empty config\n")
            no_header = subprocess.run(
                ["bash", str(root / "ssh-forward"), "add", "8080", "127.0.0.1", "80", "web"],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(no_header.returncode, 0)
            conf.unlink()

            # Add with --host creates 0600 forwards.conf and restarts service
            good_add = subprocess.run(
                ["bash", str(root / "ssh-forward"), "add", "--host", "ubuntu@10.0.0.5", "8080", "127.0.0.1", "80", "web"],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(good_add.returncode, 0, good_add.stdout + good_add.stderr)
            self.assertTrue(conf.exists())
            self.assertEqual(stat.S_IMODE(conf.stat().st_mode), 0o600)
            self.assertEqual(conf.read_text(), "SSH_HOST=ubuntu@10.0.0.5\n8080|127.0.0.1|80|web\n")
            self.assertIn("restart ssh-forwarder.service", sys_log.read_text())

            # List shows rule
            res_list = subprocess.run(
                ["bash", str(root / "ssh-forward"), "list"],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(res_list.returncode, 0)
            self.assertIn("ubuntu@10.0.0.5", res_list.stdout)
            self.assertIn("8080", res_list.stdout)

            # Delete rule removes it and restarts service
            res_del = subprocess.run(
                ["bash", str(root / "ssh-forward"), "del", "8080"],
                env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(res_del.returncode, 0, res_del.stdout + res_del.stderr)
            self.assertNotIn("8080|", conf.read_text())

    def test_setup_key_writes_host_alias_not_host_part(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(REPO_ROOT / "setup-key.sh", root)
            ssh_dir = root / "ssh_dir"

            fake_keygen = root / "ssh-keygen"
            fake_keygen.write_text(
                f"#!{sys.executable}\n"
                "import pathlib, sys\n"
                "key_path = pathlib.Path(sys.argv[sys.argv.index('-f') + 1])\n"
                "key_path.write_text('PRIVATE\\n')\n"
                "pathlib.Path(str(key_path) + '.pub').write_text('ssh-ed25519 AAAATEST test\\n')\n"
            )
            fake_copy = root / "ssh-copy-id"
            fake_copy.write_text("#!/bin/bash\nexit 0\n")
            fake_keygen.chmod(0o755)
            fake_copy.chmod(0o755)

            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}")
            res = subprocess.run(
                ["bash", str(root / "setup-key.sh"), str(ssh_dir), "ubuntu@10.0.0.9"],
                input="id_myalias\n", env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

            cfg = (ssh_dir / "config").read_text()
            self.assertIn("Host myalias\n", cfg)
            self.assertNotIn("Host 10.0.0.9\n", cfg)
            self.assertIn("    HostName 10.0.0.9\n", cfg)
            self.assertIn("    User ubuntu\n", cfg)
            self.assertEqual(stat.S_IMODE((ssh_dir / "config").stat().st_mode), 0o600)
            self.assertIn("完成：ssh myalias", res.stdout)
