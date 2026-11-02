"""Save immutable evidence for the preflight increment, excluding active logs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path.cwd()
verification = root / 'examples/utility/verification-preflight-v1'
checks = {}
for name in ('contracts', 'accounting-contracts', 'optional', 'default-suite', 'command-path', 'interoperability'):
    suites = ET.parse(verification / (name + '.xml')).getroot()
    checks[name] = {key: sum(int(s.get(key, '0')) for s in suites.iter('testsuite')) for key in ('tests', 'failures', 'errors', 'skipped')}
assert checks['default-suite']['failures'] == 1
assert checks['command-path']['failures'] == 0
for name in ('contracts', 'accounting-contracts', 'optional', 'interoperability'):
    assert checks[name]['failures'] == checks[name]['errors'] == 0
source = root / 'src/autoengineering'
for folder in ('wind-preflight-v1', 'wind-native-preflight-v1'):
    capture = root / 'examples/utility/development' / folder / 'captured'
    for p in source.rglob('*.py'):
        assert p.read_bytes() == (capture / p.relative_to(root)).read_bytes()
summary = {
    'schema': 'utility-preflight-increment-checkpoint-v1',
    'checks': checks,
    'default_failure': 'shell command could not find python outside activated PATH; focused test passed with project bin on PATH',
    'bayes': {'status': 'running', 'session_id': 59944, 'log': 'examples/utility/verification-preflight-v1/bayes-suite.log'},
    'source_matches_both_scientific_captures': True,
    'goal': 'active',
    'confirmation': 'not_attempted',
    'utility_verdict': 'not_attempted',
}
(verification / 'checkpoint.json').write_text(json.dumps(summary, indent=2) + '\n')
predecessor = Path('examples/utility/source-inventory-four-family-closeout.json')
old = json.loads((root / predecessor).read_text())
paths = set(old['files'])
for directory in ('src/autoengineering', 'tests', 'examples/utility'):
    for p in (root / directory).rglob('*'):
        if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix != '.pyc' and not p.name.startswith('source-inventory'):
            paths.add(str(p.relative_to(root)))
paths |= {'docs/utility.md', 'docs/reviews/part-5-progress.md', 'docs/reviews/part-5-completion-audit.md'}
excluded = {'examples/utility/verification-preflight-v1/bayes-suite.log', 'examples/utility/verification-preflight-v1/bayes-suite.xml'}
files = {}
for name in sorted(paths - excluded):
    p = root / name
    assert p.is_file() and not p.is_symlink(), name
    files[name] = hashlib.sha256(p.read_bytes()).hexdigest()
result = {
    'schema': 'utility-increment-source-inventory-v1',
    'increment': 'preflight-geometry-checkpoint-bayes-running',
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'predecessor': {'path': str(predecessor), 'sha256': hashlib.sha256((root / predecessor).read_bytes()).hexdigest()},
    'files': files,
    'excluded_active_outputs': sorted(excluded),
    'goal': 'active',
}
output = root / 'examples/utility/source-inventory-preflight-checkpoint.json'
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + '\n')
assert all(hashlib.sha256((root / p).read_bytes()).hexdigest() == h for p, h in files.items())
print(json.dumps({'checks': checks, 'files_verified': len(files), 'inventory': str(output.relative_to(root)), 'bayes': 'running'}))
