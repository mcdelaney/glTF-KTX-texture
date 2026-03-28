import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import texture_reuse


class _FakeImage:
    def __init__(self, props):
        self._props = props

    def get(self, key):
        return self._props.get(key)


class TextureReuseTests(unittest.TestCase):
    def test_capture_import_metadata_for_external_uri(self):
        metadata = texture_reuse.capture_import_metadata(
            "textures/basecolor.ktx2",
            os.path.join("project", "scene.gltf"),
        )
        self.assertEqual(
            metadata[texture_reuse.KTX2_SOURCE_URI_PROP],
            "textures/basecolor.ktx2",
        )
        self.assertTrue(
            metadata[texture_reuse.KTX2_SOURCE_PATH_PROP].endswith(
                os.path.join("project", "textures", "basecolor.ktx2")
            )
        )

    def test_capture_import_metadata_ignores_data_uri(self):
        metadata = texture_reuse.capture_import_metadata(
            "data:image/ktx2;base64,abc",
            os.path.join("project", "scene.gltf"),
        )
        self.assertIsNone(metadata)

    def test_get_image_metadata(self):
        image = _FakeImage(
            {
                texture_reuse.KTX2_SOURCE_URI_PROP: "textures/normal.ktx2",
                texture_reuse.KTX2_SOURCE_PATH_PROP: os.path.join("project", "textures", "normal.ktx2"),
            }
        )
        metadata = texture_reuse.get_image_metadata(image)
        self.assertEqual(metadata["uri"], "textures/normal.ktx2")
        self.assertTrue(metadata["path"].endswith(os.path.join("project", "textures", "normal.ktx2")))

    def test_resolve_export_uri_rebases_relative_to_new_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            asset_dir = os.path.join(tmpdir, "assets")
            export_dir = os.path.join(tmpdir, "exports")
            os.makedirs(os.path.join(asset_dir, "textures"), exist_ok=True)
            os.makedirs(export_dir, exist_ok=True)

            source_path = os.path.join(asset_dir, "textures", "orm.ktx2")
            export_path = os.path.join(export_dir, "scene.gltf")

            uri = texture_reuse.resolve_export_uri(
                "textures/orm.ktx2",
                source_path,
                export_path,
            )
            self.assertEqual(uri, "../assets/textures/orm.ktx2")

    def test_resolve_export_uri_falls_back_to_original_uri(self):
        uri = texture_reuse.resolve_export_uri(
            "textures/basecolor.ktx2",
            None,
            os.path.join("exports", "scene.gltf"),
        )
        self.assertEqual(uri, "textures/basecolor.ktx2")


if __name__ == "__main__":
    unittest.main()
