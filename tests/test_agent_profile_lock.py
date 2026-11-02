"""Fresh profiles bind current locks without changing historical templates."""
import hashlib

from autoengineering.campaign.spec import CampaignSpec
from examples.agent_campaign import prepare_leafriver as leaf


def test_fresh_preparation_captures_current_lock_without_rewriting_template(tmp_path):
    tmp_path.chmod(0o700)
    template_path = leaf.ROOT / leaf.TEMPLATE
    original = template_path.read_bytes()
    historical = CampaignSpec.from_yaml(template_path)
    prepared = leaf.prepare(tmp_path / "prepared")
    current = hashlib.sha256((leaf.ROOT / "pixi.lock").read_bytes()).hexdigest()
    assert hashlib.sha256(original).hexdigest() == leaf.TEMPLATE_SHA256
    assert template_path.read_bytes() == original
    assert historical.provenance.environment_lock.sha256 != current
    assert leaf.load(tmp_path / "prepared", expected_digest=prepared.digest) == prepared
    assert len(prepared.routes) == 3
    for route in prepared.routes:
        spec = CampaignSpec.from_yaml(tmp_path / "prepared" / route.specification.path)
        assert spec.provenance.environment_lock.sha256 == current
        assert spec.baseline.model.dependency_bundle == current
