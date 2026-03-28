import sys
import unittest
from pathlib import Path
from unittest import mock
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ktx_tools


class KtxToolsCommandTests(unittest.TestCase):
    def test_build_toktx_basisu_command(self):
        cmd = ktx_tools.build_toktx_command(
            Path("toktx"),
            Path("input.png"),
            Path("out.ktx2"),
            {
                "target_format": "BASISU",
                "format": "UASTC",
                "quality": 2,
                "compression": 3,
                "mipmaps": True,
                "oetf": "linear",
                "target_type": "RG",
                "scale": 0.5,
            },
        )
        self.assertIn("--encode", cmd)
        self.assertIn("uastc", cmd)
        self.assertIn("--genmipmap", cmd)
        self.assertEqual(cmd[-2:], ["out.ktx2", "input.png"])

    def test_build_compressonator_command(self):
        cmd = ktx_tools.build_compressonator_command(
            Path("CompressonatorCLI.exe"),
            Path("input.png"),
            Path("out.ktx2"),
            {
                "bc_format": "BC5",
                "mipmaps": False,
                "oetf": "linear",
            },
        )
        self.assertEqual(cmd[:5], ["CompressonatorCLI.exe", "-fd", "BC5", "-EncodeWith", "CPU"])
        self.assertIn("-nomipmap", cmd)
        self.assertNotIn("-UseSRGBFrames", cmd)
        self.assertEqual(cmd[-2:], ["input.png", "out.ktx2"])

    def test_ktx2_magic_detection(self):
        self.assertTrue(ktx_tools.is_ktx2_bytes(ktx_tools.KTX2_MAGIC + b"x"))
        self.assertFalse(ktx_tools.is_ktx2_bytes(b"not-ktx2"))

    def test_compressonator_version_constant(self):
        self.assertEqual(ktx_tools.COMPRESSONATOR_VERSION, "4.5.52")

    def test_windows_compressonator_download_info_uses_zip_asset(self):
        with mock.patch.object(ktx_tools, "get_platform_info", return_value=("Windows", "x86_64")):
            url, archive_type = ktx_tools.get_compressonator_download_info()
        self.assertEqual(archive_type, "zip")
        self.assertTrue(url.endswith("compressonatorcli-4.5.52-win64.zip"))

    def test_patch_ktx2_srgb_metadata_for_bc7(self):
        sample = bytearray(160)
        sample[:len(ktx_tools.KTX2_MAGIC)] = ktx_tools.KTX2_MAGIC
        sample[12:16] = (145).to_bytes(4, "little")
        sample[48:52] = (104).to_bytes(4, "little")
        sample[52:56] = (44).to_bytes(4, "little")
        sample[104:108] = (44).to_bytes(4, "little")
        sample[112:114] = (2).to_bytes(2, "little")
        sample[114:116] = (40).to_bytes(2, "little")
        sample[118] = 1

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.ktx2"
            path.write_bytes(sample)
            ok, err = ktx_tools.patch_ktx2_srgb_metadata(path)
            self.assertTrue(ok, err)
            patched = path.read_bytes()

        self.assertEqual(int.from_bytes(patched[12:16], "little"), 146)
        self.assertEqual(int.from_bytes(patched[114:116], "little"), 40)
        self.assertEqual(patched[118], ktx_tools.KHR_DF_TRANSFER_SRGB)


if __name__ == "__main__":
    unittest.main()
