"""Merge pytest JUnit and coverage.py XML into AMI's version 1 CI report.

Coverage XML comes from coverage combine, so executed lines are unioned.
No third-party packages are needed by this script.
"""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def read_junit(path):
    """Read testcase outcomes (including collection/setup errors) once each."""
    root = ET.parse(path).getroot()
    if root.tag not in {'testsuite', 'testsuites'}:
        raise ValueError('not JUnit')
    counts = {'passed': 0, 'failed': 0, 'skipped': 0}
    failures = []
    for case in root.iter('testcase'):
        problems = case.findall('failure') + case.findall('error')
        if problems:
            counts['failed'] += 1
            message = '\n'.join(p.text or p.get('message', '') for p in problems)
            line = case.get('line')
            file = case.get('file')
            # xunit2 omits location attributes; pytest's short traceback carries
            # one-based failure locations, including setup/collection errors.
            locations = re.findall(r'^(.+?\.py):(\d+)(?::|\s|$)', message, re.MULTILINE)
            if file is None and locations:
                file, line = locations[-1]
            failures.append({
                'name': '.'.join(filter(None, [case.get('classname'), case.get('name', '')])),
                'file': file,
                'line': int(line) if line is not None else None,
                'message': message if len(message) <= 2000 else message[:1999] + '…',
            })
        elif case.find('skipped') is not None:
            counts['skipped'] += 1
        else:
            counts['passed'] += 1
    return counts, failures


def read_coverage(path):
    """Validate the combined Cobertura totals."""
    root = ET.parse(path).getroot()
    if root.tag != 'coverage':
        raise ValueError('not coverage XML')
    totals = [int(root.attrib[key]) for key in
              ('lines-covered', 'lines-valid', 'branches-covered', 'branches-valid')]
    for covered, valid in (totals[:2], totals[2:]):
        if not 0 <= covered <= valid:
            raise ValueError('invalid coverage totals')
    return totals


def build_report(parts, commit):
    """Keep usable parts when another part is missing or malformed."""
    report = {'version': 1, 'commit': commit,
              'tests': {'passed': 0, 'failed': 0, 'skipped': 0}, 'failures': [],
              'coverage': {'lines': None, 'branches': None, 'functions': None}}
    errors = []
    junit_paths = sorted(parts.rglob('junit-*.xml'))
    coverage_paths = [parts / 'coverage.xml']
    junit_ok = bool(junit_paths)
    coverage_ok = True
    for path in junit_paths:
        try:
            counts, failures = read_junit(path)
        except (OSError, ET.ParseError, ValueError):
            junit_ok = False
            continue
        for key, count in counts.items():
            report['tests'][key] += count
        report['failures'].extend(failures)
    report['failures'] = report['failures'][:50]
    missing = {'junit-a-l.xml', 'junit-m-z.xml'} - {path.name for path in junit_paths}
    if missing and junit_ok:
        errors.append('missing test parts: ' + ', '.join(sorted(missing)))
    totals = [0, 0, 0, 0]
    for path in coverage_paths:
        try:
            counts = read_coverage(path)
        except (OSError, ET.ParseError, ValueError, KeyError):
            coverage_ok = False
            continue
        totals = counts
    for key, covered, valid in [('lines', *totals[:2]), ('branches', *totals[2:])]:
        if valid:
            report['coverage'][key] = round(100 * covered / valid, 1)
    if not junit_ok:
        errors.append('no junit output')
    if not coverage_ok:
        errors.append('no coverage output')
    if errors:
        report['error'] = '; '.join(errors)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parts', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, default=Path('ami-ci-report.json'))
    args = parser.parse_args()
    args.output.write_text(json.dumps(build_report(args.parts, args.commit), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
