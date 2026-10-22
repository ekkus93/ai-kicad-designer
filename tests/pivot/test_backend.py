import pytest

from ai_kicad.pivot.backend import (
    DIRECT_PILOT_MANIFEST,
    SupportLevel,
    UnsupportedCapability,
)


def test_verified_capability_and_explicit_runtime_preconditions():
    capability = DIRECT_PILOT_MANIFEST.capability("create_project")
    assert capability.support is SupportLevel.VERIFIED
    assert capability.runtime == "headless"
    assert capability.kicad_versions == ["10.0.6"]


def test_experimental_and_unsupported_are_never_silently_downgraded():
    with pytest.raises(UnsupportedCapability, match="required verified") as error:
        DIRECT_PILOT_MANIFEST.capability("native_schematic_ipc")
    assert error.value.response()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert (
        DIRECT_PILOT_MANIFEST.capability(
            "native_schematic_ipc", required=SupportLevel.EXPERIMENTAL
        ).support
        is SupportLevel.EXPERIMENTAL
    )
    with pytest.raises(UnsupportedCapability, match="uniquely declared"):
        DIRECT_PILOT_MANIFEST.capability("autoroute_everything")
