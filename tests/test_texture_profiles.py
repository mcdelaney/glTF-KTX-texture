import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import texture_profiles


class TextureProfilesTests(unittest.TestCase):
    def test_detect_texture_role(self):
        self.assertEqual(
            texture_profiles.detect_texture_role(["Base Color", "Alpha"]),
            texture_profiles.ROLE_BASECOLOR,
        )
        self.assertEqual(
            texture_profiles.detect_texture_role(["Normal"]),
            texture_profiles.ROLE_NORMAL,
        )
        self.assertEqual(
            texture_profiles.detect_texture_role(["Metallic", "Roughness"]),
            texture_profiles.ROLE_ORM,
        )

    def test_normal_bc5_auto_uses_rg(self):
        settings = texture_profiles.resolve_texture_settings(
            ["Normal"],
            3,
            {
                "target_format": "BCN",
                "bc_format": "BC5",
                "target_type": "Auto",
                "target_oetf": "Auto",
                "basisu_mode": "Auto",
            },
        )
        self.assertEqual(settings["target_type"], "RG")
        self.assertEqual(settings["oetf"], "linear")
        self.assertIsNone(settings["error"])

    def test_bc5_rgb_is_rejected(self):
        settings = texture_profiles.resolve_texture_settings(
            ["Normal"],
            3,
            {
                "target_format": "BCN",
                "bc_format": "BC5",
                "target_type": "RGB",
                "target_oetf": "Auto",
                "basisu_mode": "Auto",
            },
        )
        self.assertEqual(
            settings["error"],
            "BC5 requires target channels RG, got RGB.",
        )

    def test_basecolor_defaults_to_srgb_and_etc1s_for_basisu(self):
        settings = texture_profiles.resolve_texture_settings(
            ["Base Color"],
            4,
            {
                "target_format": "BASISU",
                "bc_format": "BC7",
                "target_type": "Auto",
                "target_oetf": "Auto",
                "basisu_mode": "Auto",
            },
        )
        self.assertEqual(settings["oetf"], "srgb")
        self.assertEqual(settings["compression_mode"], "ETC1S")
        self.assertEqual(settings["target_type"], "RGBA")

    def test_legacy_state_detection(self):
        self.assertTrue(texture_profiles.is_legacy_format_state(texture_profiles.LEGACY_FORMAT_STATE))
        self.assertFalse(
            texture_profiles.is_legacy_format_state(
                {
                    **texture_profiles.LEGACY_FORMAT_STATE,
                    "target_format": "BCN",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
