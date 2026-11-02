"""Run the final fixture set against the already verified, unchanged wheel bytes."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

project = Path.cwd()
record = project / 'examples/utility/verification-second-host-v1'
root = Path('/private/tmp/utility-claude-installed-v3')
source = project / 'tests/test_agent_claude.py'
target = root / 'test_agent_claude_final.py'
assert not target.exists()
shutil.copyfile(source, target)
with (record / 'installed-final-tests.log').open('w') as log:
    subprocess.run([str(root/'venv/bin/python'), '-m', 'pytest', str(target), '-q', '-p', 'no:cacheprovider', '--junitxml='+str(root/'final-tests.xml')], cwd=root, env=os.environ|{'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}, check=True, stdout=log, stderr=subprocess.STDOUT)
shutil.copyfile(root/'final-tests.xml', record/'installed-final-tests.xml')
shutil.copyfile(target, record/'installed-test-source.py')
suite = ET.parse(root/'final-tests.xml').getroot().find('testsuite')
assert int(suite.get('errors')) == int(suite.get('failures')) == 0
result = {'status':'passed','tests':int(suite.get('tests')),'test_source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'wheel_sha256':json.loads((record/'installed-summary.json').read_text())['wheel_sha256'],'scope':'authored fixture set including saved-completion owner loss; no actual Claude inference','boundary_scope':'existing Python audit policy in parent and ordinary Python children, not an OS private boundary; fixed helper verifier uses isolated Python'}
(record/'installed-final-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
