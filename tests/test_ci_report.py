"""Contract tests for the artifact consumed by AMI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'ci_report.py'


def run_report(tmp_path):
    output = tmp_path / 'ami-ci-report.json'
    subprocess.run([sys.executable, str(SCRIPT), '--parts', str(tmp_path),
                    '--commit', 'a' * 40, '--output', str(output)], check=True)
    return json.loads(output.read_text())


def test_merges_counts_locations_and_coverage(tmp_path):
    (tmp_path / 'junit-a-l.xml').write_text('''<testsuites><testsuite>
      <testcase name="pass"/><testcase name="skip"><skipped/></testcase>
      <testcase classname="tests.test_x" name="test_bad" file="tests/test_x.py" line="12">
        <failure message="broken">traceback details</failure></testcase>
      <testcase name="setup"><error message="setup failed"/></testcase>
    </testsuite></testsuites>''')
    (tmp_path / 'junit-m-z.xml').write_text('<testsuite><testcase name="another"/></testsuite>')
    (tmp_path / 'coverage.xml').write_text(
        '<coverage lines-covered="9" lines-valid="10" branches-covered="3" branches-valid="4"/>')
    report = run_report(tmp_path)
    assert report['version'] == 1
    assert report['commit'] == 'a' * 40
    assert report['tests'] == {'passed': 2, 'failed': 2, 'skipped': 1}
    assert report['failures'][0] == {'name': 'tests.test_x.test_bad', 'file': 'tests/test_x.py',
                                     'line': 12, 'message': 'traceback details'}
    assert report['failures'][1]['message'] == 'setup failed'
    assert report['coverage'] == {'lines': 90.0, 'branches': 75.0, 'functions': None}
    assert 'error' not in report


def test_clips_failures_and_messages(tmp_path):
    cases = ''.join(f'<testcase name="test_{i}"><failure>{"x" * 2100}</failure></testcase>' for i in range(60))
    (tmp_path / 'junit-a-l.xml').write_text(f'<testsuite>{cases}</testsuite>')
    report = run_report(tmp_path)
    assert report['tests']['failed'] == 60
    assert len(report['failures']) == 50
    assert report['failures'][0]['message'] == 'x' * 1999 + '…'


@pytest.mark.parametrize('contents', [None, '<broken', '<wrong/>'])
def test_missing_or_garbled_inputs_still_write_report(tmp_path, contents):
    if contents is not None:
        (tmp_path / 'junit-a-l.xml').write_text(contents)
        (tmp_path / 'coverage.xml').write_text(contents)
    report = run_report(tmp_path)
    assert report['tests'] == {'passed': 0, 'failed': 0, 'skipped': 0}
    assert report['failures'] == []
    assert report['coverage'] == {'lines': None, 'branches': None, 'functions': None}
    assert report['error'] == 'no junit output; no coverage output'


def test_zero_denominators_are_unknown(tmp_path):
    (tmp_path / 'junit-a-l.xml').write_text('<testsuite/>')
    (tmp_path / 'junit-m-z.xml').write_text('<testsuite/>')
    (tmp_path / 'coverage.xml').write_text(
        '<coverage lines-covered="0" lines-valid="0" branches-covered="0" branches-valid="0"/>')
    report = run_report(tmp_path)
    assert report['coverage'] == {'lines': None, 'branches': None, 'functions': None}
    assert 'error' not in report


def test_real_pytest_xunit2_failure(tmp_path):
    fixture = Path(__file__).parent / 'fixtures' / 'ci_report' / 'junit-xunit2.xml'
    (tmp_path / 'junit-a-l.xml').write_bytes(fixture.read_bytes())
    report = run_report(tmp_path)
    failure = report['failures'][0]
    assert failure['file'] == 'tests/test_ci_failure.py'
    assert failure['line'] == 2
    assert 'AssertionError: deliberate CI failure' in failure['message']
    assert 'missing test parts: junit-m-z.xml' in report['error']


def test_combined_coverage_unions_disjoint_execution(tmp_path):
    source = tmp_path / 'sample.py'
    source.write_text('import os\nif os.environ["HALF"] == "a-l":\n    value = 1\nelse:\n    value = 2\n')
    import os

    for group in ('a-l', 'm-z'):
        env = dict(os.environ, HALF=group, COVERAGE_FILE=str(tmp_path / f'.coverage.{group}'))
        subprocess.run([sys.executable, '-m', 'coverage', 'run', '--branch', str(source)],
                       cwd=tmp_path, env=env, check=True)
        (tmp_path / f'junit-{group}.xml').write_text('<testsuite><testcase name="pass"/></testsuite>')
    subprocess.run([sys.executable, '-m', 'coverage', 'combine', '.'], cwd=tmp_path, check=True)
    subprocess.run([sys.executable, '-m', 'coverage', 'xml', '-o', 'coverage.xml'], cwd=tmp_path, check=True)
    report = run_report(tmp_path)
    assert report['coverage'] == {'lines': 100.0, 'branches': 100.0, 'functions': None}
    assert 'error' not in report
