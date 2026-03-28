# Copyright 2024 The glTF-Blender-IO authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
KTX2 Texture Support for glTF-Blender-IO

This addon adds KTX2 texture support to glTF export/import via the KHR_texture_basisu extension.
It uses the official Khronos KTX-Software command-line tools for encoding/decoding.

The tools are automatically downloaded on first use (~7MB).
"""

import bpy
import importlib

from . import texture_profiles, texture_reuse


def _reload_submodules():
    """Reload all submodules to pick up code changes during development."""
    import sys

    # List of submodule names (without package prefix)
    submodule_names = ['texture_profiles', 'texture_reuse', 'ktx_tools', 'ktx2_encode', 'ktx2_decode', 'ktx2_envmap_encode', 'ktx2_envmap_decode']

    # Get the package name (this module's package)
    package = __name__

    for name in submodule_names:
        full_name = f"{package}.{name}"
        if full_name in sys.modules:
            print(f"KTX2 Extension: Reloading {name}")
            importlib.reload(sys.modules[full_name])

bl_info = {
    "name": "glTF KTX2 Texture Extension",
    "category": "Import-Export",
    "version": (1, 0, 12),
    "blender": (4, 0, 0),
    "location": "File > Export/Import > glTF 2.0",
    "description": "Add KTX2 texture support via KHR_texture_basisu extension",
    "tracker_url": "https://github.com/KhronosGroup/glTF-Blender-IO/issues/",
    "isDraft": False,
    "developer": "glTF-Blender-IO Contributors",
    "url": "https://github.com/KhronosGroup/glTF-Blender-IO",
}

# glTF extension name following Khronos naming convention
glTF_extension_name = "KHR_texture_basisu"

# KTX2 textures require the extension for proper viewing
extension_is_required = False

# Track installation state
_tools_available = None
_bcn_tools_available = None
_installation_in_progress = False
_bcn_installation_in_progress = False
_registered_panel_classes = []


def check_tools_available(force_recheck=False):
    """Check if KTX tools are available."""
    global _tools_available
    if _tools_available is None or force_recheck:
        from . import ktx_tools
        _tools_available = ktx_tools.are_tools_installed()
    return _tools_available


def check_bcn_tools_available(force_recheck=False):
    """Check if the BCn encoder backend is available."""
    global _bcn_tools_available
    if _bcn_tools_available is None or force_recheck:
        from . import ktx_tools
        _bcn_tools_available = ktx_tools.are_bcn_tools_installed()
    return _bcn_tools_available


class KTX2_OT_install_tools(bpy.types.Operator):
    """Download and install KTX tools for KTX2 texture support"""
    bl_idname = "ktx2.install_tools"
    bl_label = "Download KTX Tools"
    bl_description = "Download KTX-Software tools (~7MB) for KTX2 encoding/decoding"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global _installation_in_progress
        _installation_in_progress = True

        from . import ktx_tools

        try:
            self.report({'INFO'}, "Downloading KTX tools... This may take a moment.")

            def progress_callback(message, percent):
                # Can't easily update UI from here, but we report at key points
                pass

            success, error = ktx_tools.install_tools(progress_callback)

            if success:
                check_tools_available(force_recheck=True)
                self.report({'INFO'}, "KTX tools installed successfully!")
            else:
                self.report({'ERROR'}, f"Installation failed: {error}")
                print(f"\nKTX Tools Installation Error: {error}\n")

        except Exception as e:
            self.report({'ERROR'}, f"Installation failed: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            _installation_in_progress = False

        return {'FINISHED'}


class KTX2_OT_check_installation(bpy.types.Operator):
    """Check if KTX tools are installed"""
    bl_idname = "ktx2.check_installation"
    bl_label = "Check Installation"
    bl_description = "Recheck if KTX tools are available"

    def execute(self, context):
        check_tools_available(force_recheck=True)
        if check_tools_available():
            self.report({'INFO'}, "KTX tools are installed and ready!")
        else:
            self.report({'WARNING'}, "KTX tools are not available. Click 'Download KTX Tools' to install.")
        return {'FINISHED'}


class KTX2_OT_check_bcn_installation(bpy.types.Operator):
    """Check if BCn tools are installed"""
    bl_idname = "ktx2.check_bcn_installation"
    bl_label = "Check BCn Installation"
    bl_description = "Recheck if CompressonatorCLI is available"

    def execute(self, context):
        check_bcn_tools_available(force_recheck=True)
        if check_bcn_tools_available():
            self.report({'INFO'}, "CompressonatorCLI is installed and ready!")
        else:
            self.report({'WARNING'}, "CompressonatorCLI is not available. Click 'Download BCn Tools' to install.")
        return {'FINISHED'}


class KTX2_OT_install_bcn_tools(bpy.types.Operator):
    """Download and install CompressonatorCLI for BCn texture support"""
    bl_idname = "ktx2.install_bcn_tools"
    bl_label = "Download BCn Tools"
    bl_description = "Download CompressonatorCLI for native BCn texture encoding"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global _bcn_installation_in_progress
        _bcn_installation_in_progress = True

        from . import ktx_tools

        try:
            self.report({'INFO'}, "Downloading BCn tools... This may take a moment.")

            def progress_callback(message, percent):
                pass

            success, error = ktx_tools.install_compressonator(progress_callback)

            if success:
                check_bcn_tools_available(force_recheck=True)
                self.report({'INFO'}, "BCn tools installed successfully!")
            else:
                self.report({'ERROR'}, f"Installation failed: {error}")
                print(f"\nBCn Tools Installation Error: {error}\n")

        except Exception as e:
            self.report({'ERROR'}, f"Installation failed: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            _bcn_installation_in_progress = False

        return {'FINISHED'}

class KTX2ExportCompressionETC1S(bpy.types.PropertyGroup):
    quality_level: bpy.props.IntProperty(
        name="Quality",
        description="ETC1S: 1-255 (higher=better)",
        min=1,
        max=255,
        default=128
    )
    compression_level: bpy.props.IntProperty(
        name="Compression",
        description="ETC1S: 0-5 (higher=better)",
        min=0,
        max=5,
        default=3
    )

class KTX2ExportCompressionUASTC(bpy.types.PropertyGroup):
    quality_level: bpy.props.IntProperty(
        name="Quality",
        description="UASTC: 0-4 (higher=better)",
        min=0,
        max=4,
        default=2
    )
    compression_level: bpy.props.IntProperty(
        name="Compression",
        description="UASTC: 1-22 (higher=better)",
        min=1,
        max=22,
        default=3
    )

class KTX2ExportFormatBASISU(bpy.types.PropertyGroup):
    compression_mode: bpy.props.EnumProperty(
        name="Mode",
        description="Basis Universal compression mode",
        items=[
            ("Auto", "Auto", "Automatically determine compression mode based on node name"),
            ('ETC1S', "ETC1S", "Smaller files, lower quality. Best for diffuse/color textures"),
            ('UASTC', "UASTC", "Larger files, higher quality. Best for normal maps and fine details"),
        ],
        default='Auto'
    )

    etc1s: bpy.props.PointerProperty(type=KTX2ExportCompressionETC1S)
    uastc: bpy.props.PointerProperty(type=KTX2ExportCompressionUASTC)

class KTX2ExportFormatASTC(bpy.types.PropertyGroup):
    astc_block_size: bpy.props.EnumProperty(
        name="ASTC Block Size",
        description="ASTC compression block size. Smaller blocks = higher quality, larger files",
        items=[
            ('4x4', "4x4 (Highest Quality)", "8 bits/pixel - Best quality, largest files"),
            ('5x5', "5x5 (High Quality)", "5.12 bits/pixel - High quality"),
            ('6x6', "6x6 (Balanced)", "3.56 bits/pixel - Good balance of quality and size"),
            ('8x8', "8x8 (Smaller Files)", "2 bits/pixel - Smaller files, lower quality"),
        ],
        default='6x6'
    )


class KTX2ExportFormatBCN(bpy.types.PropertyGroup):
    bc_format: bpy.props.EnumProperty(
        name="BC Format",
        description="Native BCn texture format",
        items=[
            ('BC1', "BC1", "Opaque or 1-bit alpha RGB"),
            ('BC3', "BC3", "RGBA with interpolated alpha"),
            ('BC4', "BC4", "Single-channel red"),
            ('BC5', "BC5", "Two-channel red/green. Best default for tangent-space normals"),
            ('BC7', "BC7", "High quality RGB/RGBA"),
        ],
        default='BC7'
    )

class KTX2ExportFormat(bpy.types.PropertyGroup):
    target_format: bpy.props.EnumProperty(
        name="Target Format",
        description="GPU texture format. Native formats upload directly, Basis Universal transcodes at runtime",
        items=[
            ('BASISU', "Basis Universal", "Universal format that transcodes to any GPU (BC7, ASTC, ETC2, etc.) at runtime. Best compatibility"),
            ('ASTC', "Native ASTC", "Direct GPU upload on ASTC hardware (mobile, Apple Silicon). No transcoding needed"),
            ('BCN', "Native BCn", "Direct GPU upload on BC-capable desktop hardware. Requires CompressonatorCLI"),
        ],
        default='BASISU'
    )

    target_type: bpy.props.EnumProperty(
        name="Channels",
        description="Target channel types",
        items=[
            ('Auto', "Auto", "Automatically gather channel count based on nodes attached to texture"),
            ('R', "R", "R Channel"),
            ('RG', "RG", "RG Channels"),
            ('RGB', "RGB", "RGB Channels"),
            ('RGBA', "RGBA", "RGBA Channels"),
        ],
        default='Auto'
    )

    target_oetf: bpy.props.EnumProperty(
        name="Gamma",
        description="Target gamma colorspace",
        items=[
            ('Auto', "Auto", "Automatically use gamma based on node name"),
            ('linear', "Linear", "Linear gamma"),
            ('srgb', "sRGB", "sRGB gamma"),
        ],
        default='Auto'
    )

    downsample_factor: bpy.props.IntProperty(
        name="Downsample",
        description="Downsample factor (1-4)",
        min=1,
        max=4,
        default=1
    )

    astc: bpy.props.PointerProperty(type=KTX2ExportFormatASTC)
    bcn: bpy.props.PointerProperty(type=KTX2ExportFormatBCN)
    basisu: bpy.props.PointerProperty(type=KTX2ExportFormatBASISU)

class KTX2ExportProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="KTX2 Textures",
        description="Export textures in KTX2 format using KHR_texture_basisu extension",
        default=False
    )

    basecolor: bpy.props.PointerProperty(type=KTX2ExportFormat)
    normal: bpy.props.PointerProperty(type=KTX2ExportFormat)
    orm: bpy.props.PointerProperty(type=KTX2ExportFormat)
    other: bpy.props.PointerProperty(type=KTX2ExportFormat)
    defaults_version: bpy.props.IntProperty(default=0, options={'HIDDEN'})

    reuse_imported_ktx2: bpy.props.BoolProperty(
        name="Reuse Imported KTX2",
        description="Reuse imported external KTX2 references and skip re-encoding those textures during export",
        default=False
    )

    create_fallback: bpy.props.BoolProperty(
        name="Create Fallback",
        description="Keep original PNG/JPEG texture as fallback for viewers without KTX2 support",
        default=True
    )

    generate_mipmaps: bpy.props.BoolProperty(
        name="Generate Mipmaps",
        description="Pre-generate mipmaps in KTX2 file. Faster load times but ~33% larger files",
        default=False
    )

    export_environment_map: bpy.props.BoolProperty(
        name="Export Environment Map",
        description="Export world environment texture as KTX2 cubemap (KHR_environment_map extension - experimental)",
        default=False
    )

    envmap_resolution: bpy.props.EnumProperty(
        name="Cubemap Resolution",
        description="Resolution of each cubemap face",
        items=[
            ('256', "256", "256x256 per face (fast, low quality)"),
            ('512', "512", "512x512 per face (balanced)"),
            ('1024', "1024", "1024x1024 per face (high quality)"),
            ('2048', "2048", "2048x2048 per face (very high quality)"),
        ],
        default='512'
    )


class KTX2ImportProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="KTX2 Textures",
        description="Import KTX2 textures from KHR_texture_basisu extension",
        default=True
    )

    prefer_ktx2: bpy.props.BoolProperty(
        name="Prefer KTX2",
        description="When both KTX2 and fallback textures exist, prefer KTX2 source",
        default=True
    )


def draw_install_tools_ui(layout):
    """Draw the KTX tools installation UI."""
    box = layout.box()
    box.label(text="KTX tools required", icon='INFO')

    if _installation_in_progress:
        box.label(text="Downloading... please wait")
        box.enabled = False
    else:
        col = box.column(align=True)
        col.operator("ktx2.install_tools", icon='IMPORT')
        col.operator("ktx2.check_installation", icon='FILE_REFRESH')
        col.label(text="One-time download (~7MB)", icon='URL')


def draw_bcn_install_tools_ui(layout):
    """Draw the BCn tools installation UI."""
    box = layout.box()
    box.label(text="BCn tools required", icon='INFO')

    if _bcn_installation_in_progress:
        box.label(text="Downloading... please wait")
        box.enabled = False
    else:
        col = box.column(align=True)
        col.operator("ktx2.install_bcn_tools", icon='IMPORT')
        col.operator("ktx2.check_bcn_installation", icon='FILE_REFRESH')
        col.label(text="One-time download (~25MB)", icon='URL')


def _format_state(format_props):
    return {
        'target_format': format_props.target_format,
        'target_type': format_props.target_type,
        'target_oetf': format_props.target_oetf,
        'downsample_factor': format_props.downsample_factor,
        'basisu_mode': format_props.basisu.compression_mode,
        'astc_block_size': format_props.astc.astc_block_size,
        'bc_format': format_props.bcn.bc_format,
    }


def ensure_export_defaults(props):
    if props.defaults_version >= texture_profiles.EXPORT_DEFAULTS_VERSION:
        return

    for role_name in (
        texture_profiles.ROLE_BASECOLOR,
        texture_profiles.ROLE_NORMAL,
        texture_profiles.ROLE_ORM,
        texture_profiles.ROLE_OTHER,
    ):
        format_props = getattr(props, role_name)
        if not texture_profiles.is_legacy_format_state(_format_state(format_props)):
            continue

        defaults = texture_profiles.get_role_defaults(role_name)
        format_props.target_format = defaults['target_format']
        if defaults['target_format'] == 'BCN':
            format_props.bcn.bc_format = defaults['bc_format']

    props.defaults_version = texture_profiles.EXPORT_DEFAULTS_VERSION


def _apply_export_defaults_to_scene(scene):
    props = getattr(scene, "KTX2ExportProperties", None)
    if props is None:
        return
    ensure_export_defaults(props)


@bpy.app.handlers.persistent
def _apply_export_defaults_on_load(_dummy=None):
    for scene in bpy.data.scenes:
        _apply_export_defaults_to_scene(scene)


def _apply_export_defaults_deferred():
    try:
        for scene in bpy.data.scenes:
            _apply_export_defaults_to_scene(scene)
    except Exception as exc:
        print(f"KTX2 Extension: Unable to apply export defaults: {exc}")
    return None


def _export_uses_bcn(props):
    return any(
        getattr(props, role_name).target_format == 'BCN'
        for role_name in (
            texture_profiles.ROLE_BASECOLOR,
            texture_profiles.ROLE_NORMAL,
            texture_profiles.ROLE_ORM,
            texture_profiles.ROLE_OTHER,
        )
    )


def _find_blender_image_for_gltf_image(gltf_image):
    import bpy

    if not gltf_image or not getattr(gltf_image, "name", None):
        return None

    blender_image = bpy.data.images.get(gltf_image.name)
    if blender_image is None and "." in gltf_image.name:
        blender_image = bpy.data.images.get(gltf_image.name.rsplit(".", 1)[0])
    return blender_image


def _build_reused_ktx2_image(gltf_image, export_settings):
    blender_image = _find_blender_image_for_gltf_image(gltf_image)
    if blender_image is None:
        return None

    metadata = texture_reuse.get_image_metadata(blender_image)
    if metadata is None:
        return None

    export_uri = texture_reuse.resolve_export_uri(
        metadata["uri"],
        metadata["path"],
        export_settings.get("gltf_filepath", ""),
    )
    if not export_uri:
        return None

    from io_scene_gltf2.io.com import gltf2_io

    name = gltf_image.name or "texture"
    if "." in name:
        name = name.rsplit(".", 1)[0]

    return gltf2_io.Image(
        buffer_view=None,
        extensions=None,
        extras=None,
        mime_type="image/ktx2",
        name=name,
        uri=export_uri,
    )

def draw_format(body, props, name, display):
    header, body = body.panel(f"GLTF_addon_ktx2_exporter_{name}",  default_closed=True)
    header.label(text=display)
    if body:
        body.prop(props, 'target_format')
        # Show format-specific options
        if props.target_format == 'BASISU':
            body.prop(props.basisu, 'compression_mode')
            # Show appropriate quality range based on mode
            if props.basisu.compression_mode == 'UASTC':
                body.prop(props.basisu.uastc, 'quality_level')
                body.prop(props.basisu.uastc, 'compression_level')
            elif props.basisu.compression_mode == 'ETC1S':
                body.prop(props.basisu.etc1s, 'quality_level')
                body.prop(props.basisu.etc1s, 'compression_level')
        elif props.target_format == 'ASTC':
            body.prop(props.astc, 'astc_block_size')
        elif props.target_format == 'BCN':
            body.prop(props.bcn, 'bc_format')
        body.prop(props, 'target_type')
        body.prop(props, 'target_oetf')
        body.prop(props, 'downsample_factor')

def draw_export(context, layout):
    """Draw export UI panel."""
    header, body = layout.panel("GLTF_addon_ktx2_exporter", default_closed=True)
    header.use_property_split = False

    props = context.scene.KTX2ExportProperties
    header.prop(props, 'enabled')

    if body is None:
        return

    if not check_tools_available():
        draw_install_tools_ui(body)
    if _export_uses_bcn(props) and not check_bcn_tools_available():
        draw_bcn_install_tools_ui(body)

    body.prop(props, 'reuse_imported_ktx2')
    if props.reuse_imported_ktx2:
        box = body.box()
        box.label(text="Imported external .ktx2 files will be reused.", icon='INFO')
        box.label(text="Reused textures skip KTX2 encoding and fallback export.")

    draw_format(body, props.basecolor, "basecolor", "Base Color")
    draw_format(body, props.normal, "normal", "Normal")
    draw_format(body, props.orm, "orm", "ORM")
    draw_format(body, props.other, "other", "Other")
    body.prop(props, 'generate_mipmaps')
    body.prop(props, 'create_fallback')

    body.separator()
    body.label(text="Environment Map (Experimental):")
    body.prop(props, 'export_environment_map')
    if props.export_environment_map:
        body.prop(props, 'envmap_resolution')


def draw_import(context, layout):
    """Draw import UI panel."""
    header, body = layout.panel("GLTF_addon_ktx2_importer", default_closed=True)
    header.use_property_split = False

    props = context.scene.KTX2ImportProperties
    header.prop(props, 'enabled')

    if body is None:
        return

    if not check_tools_available():
        draw_install_tools_ui(body)
    else:
        body.prop(props, 'prefer_ktx2')


class GLTF_PT_KTX2ExporterPanel(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'KTX2 Textures'
    bl_parent_id = 'GLTF_PT_export_user_extensions'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.KTX2ExportProperties
        self.layout.prop(props, 'enabled', text='')

    def draw(self, context):
        draw_export(context, self.layout)


class GLTF_PT_KTX2ImporterPanel(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'KTX2 Textures'
    bl_parent_id = 'GLTF_PT_import_user_extensions'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.KTX2ImportProperties
        self.layout.prop(props, 'enabled', text='')

    def draw(self, context):
        draw_import(context, self.layout)


def register_panel():
    """Register export/import UI under Blender's glTF add-on."""
    global _registered_panel_classes
    unregister_panel()

    try:
        import io_scene_gltf2
    except Exception:
        io_scene_gltf2 = None

    if io_scene_gltf2 is not None:
        try:
            io_scene_gltf2.exporter_extension_layout_draw[__name__] = draw_export
        except Exception as exc:
            print(f"KTX2 Extension: Unable to register export UI: {exc}")

        try:
            io_scene_gltf2.importer_extension_layout_draw[__name__] = draw_import
        except Exception as exc:
            print(f"KTX2 Extension: Unable to register import UI: {exc}")

    for cls, parent_id in (
        (GLTF_PT_KTX2ExporterPanel, 'GLTF_PT_export_user_extensions'),
        (GLTF_PT_KTX2ImporterPanel, 'GLTF_PT_import_user_extensions'),
    ):
        if not hasattr(bpy.types, parent_id):
            continue
        try:
            bpy.utils.register_class(cls)
            _registered_panel_classes.append(cls)
        except Exception as exc:
            print(f"KTX2 Extension: Unable to register panel {cls.__name__}: {exc}")

    return unregister_panel


def unregister_panel():
    """Unregister export/import panels if they were added."""
    global _registered_panel_classes

    for cls in reversed(_registered_panel_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

    try:
        import io_scene_gltf2
    except Exception:
        io_scene_gltf2 = None

    if io_scene_gltf2 is not None:
        io_scene_gltf2.exporter_extension_layout_draw.pop(__name__, None)
        io_scene_gltf2.importer_extension_layout_draw.pop(__name__, None)

    _registered_panel_classes = []


class glTF2ExportUserExtension:
    """Export extension for KTX2 texture support."""

    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
        self.properties = bpy.context.scene.KTX2ExportProperties
        self._processed_images = {}  # Cache to avoid processing same image twice

    def gather_texture_hook(self, gltf2_texture, blender_shader_sockets, export_settings):
        """Hook called when gathering texture data for export."""
        if not self.properties.enabled:
            return
        ensure_export_defaults(self.properties)

        if gltf2_texture.source is None:
            return

        # Get texture info
        socket_names = []
        channels = 0
        for wrapper in blender_shader_sockets:
            socket = wrapper.socket
            if not socket.links:
                continue
            if socket.name == 'Base Color':
                channels += 3
            elif socket.name == 'Alpha':
                channels += 1
            elif socket.name == "Normal":
                channels = 3
            elif socket.name == "Metallic":
                channels = 3
            elif socket.name == "Roughness":
                channels = 3
            socket_names.append(socket.name)

        role = texture_profiles.detect_texture_role(socket_names)
        format_props = getattr(self.properties, role)
        resolved = texture_profiles.resolve_texture_settings(
            socket_names,
            channels,
            _format_state(format_props),
        )

        if resolved['error']:
            export_settings['log'].warning(
                f"Skipping KTX2 encode for {getattr(gltf2_texture.source, 'name', 'unknown')}: {resolved['error']}"
            )
            return

        source_image = gltf2_texture.source

        if self.properties.reuse_imported_ktx2:
            reused_ktx2_image = _build_reused_ktx2_image(source_image, export_settings)
            if reused_ktx2_image is not None:
                if gltf2_texture.extensions is None:
                    gltf2_texture.extensions = {}

                gltf2_texture.extensions[glTF_extension_name] = self.Extension(
                    name=glTF_extension_name,
                    extension={"source": reused_ktx2_image},
                    required=True
                )
                gltf2_texture.source = None
                return

            export_settings['log'].warning(
                f"Texture {getattr(source_image, 'name', 'unknown')} has no reusable external KTX2 source; falling back to normal export."
            )

        if resolved['target_format'] in ('BASISU', 'ASTC') and not check_tools_available():
            export_settings['log'].warning("KTX2 export disabled for BasisU/ASTC: KTX tools not installed")
            return

        if resolved['target_format'] == 'BCN' and not check_bcn_tools_available():
            export_settings['log'].warning(
                "BCn export disabled: CompressonatorCLI not found. Install it and place it in PATH or the add-on bin folder."
            )
            return

        from . import ktx2_encode

        # Check if we already processed this image
        cache_key = (
            id(source_image),
            resolved['target_format'],
            resolved['bc_format'],
            resolved['compression_mode'],
            resolved['oetf'],
            resolved['target_type'],
            format_props.astc.astc_block_size,
            format_props.downsample_factor,
            self.properties.generate_mipmaps,
            format_props.basisu.uastc.quality_level,
            format_props.basisu.uastc.compression_level,
            format_props.basisu.etc1s.quality_level,
            format_props.basisu.etc1s.compression_level,
        )
        if cache_key in self._processed_images:
            ktx2_image = self._processed_images[cache_key]
        else:
            # Encode to KTX2
            quality_level = 0
            compression_level = 0
            if resolved['compression_mode'] == "UASTC":
                quality_level = format_props.basisu.uastc.quality_level
                compression_level = format_props.basisu.uastc.compression_level
            elif resolved['target_format'] == 'BASISU':
                quality_level = format_props.basisu.etc1s.quality_level
                compression_level = format_props.basisu.etc1s.compression_level

            ktx2_image = ktx2_encode.encode_image_to_ktx2(
                source_image,
                resolved['target_format'],
                resolved['compression_mode'],
                quality_level,
                compression_level,
                self.properties.generate_mipmaps,
                export_settings,
                astc_block_size=format_props.astc.astc_block_size,
                oetf=resolved['oetf'],
                target_type=resolved['target_type'],
                scale=1.0 / format_props.downsample_factor,
                bc_format=format_props.bcn.bc_format,
            )
            if ktx2_image is None:
                export_settings['log'].warning(
                    f"Failed to encode image to KTX2: {getattr(source_image, 'name', 'unknown')}"
                )
                return

            self._processed_images[cache_key] = ktx2_image

        # Add KHR_texture_basisu extension to texture
        if gltf2_texture.extensions is None:
            gltf2_texture.extensions = {}

        ext_data = {"source": ktx2_image}

        gltf2_texture.extensions[glTF_extension_name] = self.Extension(
            name=glTF_extension_name,
            extension=ext_data,
            required=not self.properties.create_fallback
        )

        # If no fallback wanted, remove the original source
        if not self.properties.create_fallback:
            gltf2_texture.source = None

    def gather_gltf_extensions_hook(self, gltf, export_settings):
        """Hook called to add root-level extensions like KHR_environment_map."""
        if not self.properties.export_environment_map:
            return

        if not check_tools_available():
            export_settings['log'].warning("Environment map export disabled: KTX tools not installed")
            return

        from . import ktx2_envmap_encode
        from io_scene_gltf2.io.com import gltf2_io

        # Export the environment map
        ktx2_bytes, env_data = ktx2_envmap_encode.export_environment_map(
            self.properties,
            export_settings
        )

        if ktx2_bytes is None:
            return

        # Create the KTX2 image for the cubemap
        if export_settings['gltf_format'] == 'GLTF_SEPARATE':
            # For separate files, write KTX2 file directly and use filename as URI
            import os
            filepath = export_settings.get('gltf_filepath', '')
            output_dir = os.path.dirname(filepath)
            ktx2_filename = "environment_cubemap.ktx2"
            ktx2_filepath = os.path.join(output_dir, ktx2_filename)

            # Write KTX2 file
            with open(ktx2_filepath, 'wb') as f:
                f.write(ktx2_bytes)

            env_image = gltf2_io.Image(
                buffer_view=None,
                extensions=None,
                extras=None,
                mime_type="image/ktx2",
                name="environment_cubemap",
                uri=ktx2_filename
            )
        else:
            # For GLB/embedded formats, we must use base64 data URI
            # Note: Using buffer_view with BinaryData doesn't work in gather_gltf_extensions_hook
            # because BinaryData processing has already completed at this stage
            import base64
            b64_data = base64.b64encode(ktx2_bytes).decode('ascii')
            data_uri = f"data:image/ktx2;base64,{b64_data}"

            env_image = gltf2_io.Image(
                buffer_view=None,
                extensions=None,
                extras=None,
                mime_type="image/ktx2",
                name="environment_cubemap",
                uri=data_uri
            )

        # Add image to glTF images array
        if gltf.images is None:
            gltf.images = []
        gltf.images.append(env_image)
        cubemap_image_index = len(gltf.images) - 1

        # Mark that we exported an environment map and schedule post-processing
        export_settings['ktx2_envmap_exported'] = True

        # Schedule post-processing to convert data URI to bufferView
        filepath = export_settings.get('gltf_filepath', '')
        gltf_format = export_settings['gltf_format']
        import sys
        print(f"KTX2 Extension: Export format={gltf_format}, filepath={filepath}")
        sys.stdout.flush()

        # Post-process for formats that use binary buffers
        if gltf_format in ('GLB', 'GLTF_EMBEDDED', 'GLTF_SEPARATE'):
            _schedule_post_process(filepath, gltf_format)

        # Create texture referencing the cubemap image by index
        # Use KHR_environment_map extension since cubemap is always KTX2 in this extension
        env_texture = gltf2_io.Texture(
            extensions={
                "KHR_environment_map": {"source": cubemap_image_index}
            },
            extras=None,
            name="environment_cubemap",
            sampler=None,
            source=None  # No fallback source, using extension only
        )

        if gltf.textures is None:
            gltf.textures = []
        gltf.textures.append(env_texture)
        cubemap_texture_index = len(gltf.textures) - 1

        # Add KHR_environment_map extension to glTF root
        if gltf.extensions is None:
            gltf.extensions = {}

        # Extension data following the proposed spec
        extension_data = {
            "environmentMaps": [
                {
                    "cubemap": cubemap_texture_index,
                    "intensity": env_data.get('intensity', 1.0),
                }
            ]
        }

        gltf.extensions["KHR_environment_map"] = self.Extension(
            name="KHR_environment_map",
            extension=extension_data,
            required=False
        )

        # Add to extensionsUsed
        if gltf.extensions_used is None:
            gltf.extensions_used = []
        if "KHR_environment_map" not in gltf.extensions_used:
            gltf.extensions_used.append("KHR_environment_map")
        sys.stdout.flush()


class _ImportExtensionInfo:
    """Simple class to hold extension info for the importer."""
    def __init__(self, name, required=True):
        self.name = name
        self.required = required


class glTF2ImportUserExtension:
    """Import extension for KTX2 texture support."""

    def __init__(self):
        self.properties = bpy.context.scene.KTX2ImportProperties
        self._decoded_images = {}  # Cache decoded images by index
        # Declare that we handle KHR_texture_basisu and KHR_environment_map extensions
        self.extensions = [
            _ImportExtensionInfo(glTF_extension_name, required=True),
            _ImportExtensionInfo("KHR_environment_map", required=False)
        ]

    def gather_import_texture_before_hook(self, gltf_texture, mh, tex_info, location, label,
                                          color_socket, alpha_socket, is_data, gltf):
        """Hook called before importing a texture - select KTX2 source if available."""
        if not self.properties.enabled:
            return

        if not check_tools_available():
            return

        # Check for KHR_texture_basisu extension
        try:
            ktx2_source = gltf_texture.extensions['KHR_texture_basisu']['source']
        except (AttributeError, KeyError, TypeError):
            return

        if ktx2_source is None:
            return

        # Check user preference for KTX2 vs fallback
        if self.properties.prefer_ktx2:
            # Prefer KTX2: use the KTX2 source
            # Store original source as fallback reference
            gltf_texture._original_source = gltf_texture.source
            gltf_texture.source = ktx2_source
        else:
            # Prefer fallback: only use KTX2 if no fallback exists
            if gltf_texture.source is None:
                gltf_texture.source = ktx2_source

    def gather_import_image_before_hook(self, gltf_img, gltf):
        """Hook called before importing an image - decode KTX2 if needed."""
        if not self.properties.enabled:
            return

        if not check_tools_available():
            return

        # Check if this is a KTX2 image
        mime_type = getattr(gltf_img, 'mime_type', None)
        if mime_type != "image/ktx2":
            return

        from . import ktx2_decode
        from io_scene_gltf2.io.imp.gltf2_io_binary import BinaryData

        # Get image index
        try:
            img_idx = gltf.data.images.index(gltf_img)
        except ValueError:
            gltf.log.warning("Could not find image index for KTX2 image")
            return

        # Check cache
        if img_idx in self._decoded_images:
            return

        # Get KTX2 binary data
        ktx2_data = BinaryData.get_image_data(gltf, img_idx)

        # If BinaryData returns None, try loading from URI (for separate files)
        if ktx2_data is None and gltf_img.uri:
            uri = gltf_img.uri
            if not uri.startswith('data:'):
                # It's a file URI, load from disk
                import os
                gltf_dir = os.path.dirname(gltf.filename)
                file_path = os.path.join(gltf_dir, uri)
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        ktx2_data = f.read()

        if ktx2_data is None:
            gltf.log.warning(f"Could not get KTX2 data for image {img_idx}")
            return

        # Convert to bytes if needed
        if hasattr(ktx2_data, 'tobytes'):
            ktx2_data = ktx2_data.tobytes()

        # Decode KTX2 to PNG
        png_data = ktx2_decode.decode_ktx2_to_png(ktx2_data, gltf)
        if png_data is None:
            gltf.log.warning(f"Failed to decode KTX2 image {img_idx}")
            return

        # Create Blender image from decoded PNG data
        # We need to write to a temp file and load it, since pack() expects raw pixels
        import tempfile
        import os

        img_name = gltf_img.name or f'KTX2_Image_{img_idx}'

        temp_png = None
        try:
            # Write PNG to temp file
            temp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_png.write(png_data)
            temp_png.close()

            # Load the image from temp file
            blender_image = bpy.data.images.load(temp_png.name)
            blender_image.name = img_name
            blender_image.alpha_mode = 'CHANNEL_PACKED'

            metadata = texture_reuse.capture_import_metadata(
                gltf_img.uri,
                getattr(gltf, "filename", None),
            )
            if metadata:
                for key, value in metadata.items():
                    blender_image[key] = value

            # Pack the image into the .blend file so the temp file can be deleted
            blender_image.pack()

            # Mark as already processed so the importer doesn't try again
            gltf_img.blender_image_name = blender_image.name
            self._decoded_images[img_idx] = blender_image.name

            # Clear the buffer_view so the main importer's create_from_data()
            # returns None and doesn't overwrite our blender_image_name
            gltf_img.buffer_view = None
            gltf_img.uri = None

        finally:
            # Clean up temp file
            if temp_png:
                try:
                    os.unlink(temp_png.name)
                except OSError:
                    pass

    def gather_import_scene_after_nodes_hook(self, gltf_scene, blender_scene, gltf):
        """Hook called after scene nodes are created - import environment map."""
        if not self.properties.enabled:
            return

        # Check for KHR_environment_map extension
        if gltf.data.extensions is None:
            return

        env_map_ext = gltf.data.extensions.get('KHR_environment_map')
        if env_map_ext is None:
            return

        from . import ktx2_envmap_decode

        try:
            ktx2_envmap_decode.import_environment_map(env_map_ext, gltf)
        except Exception as e:
            gltf.log.error(f"Failed to import environment map: {e}")
            import traceback
            traceback.print_exc()


def register():
    """Register addon classes and UI."""
    # Reload submodules to pick up code changes (for development)
    _reload_submodules()

    bpy.utils.register_class(KTX2_OT_install_tools)
    bpy.utils.register_class(KTX2_OT_install_bcn_tools)
    bpy.utils.register_class(KTX2_OT_check_installation)
    bpy.utils.register_class(KTX2_OT_check_bcn_installation)
    bpy.utils.register_class(KTX2ExportCompressionETC1S)
    bpy.utils.register_class(KTX2ExportCompressionUASTC)
    bpy.utils.register_class(KTX2ExportFormatASTC)
    bpy.utils.register_class(KTX2ExportFormatBCN)
    bpy.utils.register_class(KTX2ExportFormatBASISU)
    bpy.utils.register_class(KTX2ExportFormat)
    bpy.utils.register_class(KTX2ExportProperties)
    bpy.utils.register_class(KTX2ImportProperties)

    bpy.types.Scene.KTX2ExportProperties = bpy.props.PointerProperty(type=KTX2ExportProperties)
    bpy.types.Scene.KTX2ImportProperties = bpy.props.PointerProperty(type=KTX2ImportProperties)

    if _apply_export_defaults_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_apply_export_defaults_on_load)

    bpy.app.timers.register(_apply_export_defaults_deferred, first_interval=0.0)

    register_panel()

    # Check tools availability on load
    check_tools_available()


def unregister():
    """Unregister addon classes and UI."""
    unregister_panel()

    if _apply_export_defaults_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_apply_export_defaults_on_load)

    del bpy.types.Scene.KTX2ExportProperties
    del bpy.types.Scene.KTX2ImportProperties

    bpy.utils.unregister_class(KTX2ImportProperties)
    bpy.utils.unregister_class(KTX2ExportProperties)
    bpy.utils.unregister_class(KTX2ExportFormat)
    bpy.utils.unregister_class(KTX2ExportFormatBCN)
    bpy.utils.unregister_class(KTX2ExportFormatASTC)
    bpy.utils.unregister_class(KTX2ExportFormatBASISU)
    bpy.utils.unregister_class(KTX2ExportCompressionETC1S)
    bpy.utils.unregister_class(KTX2ExportCompressionUASTC)
    bpy.utils.unregister_class(KTX2_OT_check_bcn_installation)
    bpy.utils.unregister_class(KTX2_OT_check_installation)
    bpy.utils.unregister_class(KTX2_OT_install_bcn_tools)
    bpy.utils.unregister_class(KTX2_OT_install_tools)


def glTF2_pre_export_callback(export_settings):
    """Called before export starts."""
    # Clear the flag for environment map export
    export_settings['ktx2_envmap_exported'] = False


def glTF2_post_export_callback(export_settings):
    """Called after export completes. Post-process GLB to fix environment map bufferView."""
    _run_post_export(export_settings)


def _run_post_export(export_settings):
    """Run post-export processing."""
    # Only process if we exported an environment map in GLB format
    if not export_settings.get('ktx2_envmap_exported', False):
        return

    if export_settings['gltf_format'] not in ('GLB', 'GLTF_EMBEDDED'):
        return

    filepath = export_settings['gltf_filepath']
    if not filepath.lower().endswith('.glb'):
        return

    try:
        _post_process_glb_envmap(filepath, export_settings)
    except Exception as e:
        print(f"KTX2 Extension: Failed to post-process GLB for environment map: {e}")
        import traceback
        traceback.print_exc()


# Global storage for pending post-processing
_pending_post_process = None
_post_process_retries = 0
_MAX_POST_PROCESS_RETRIES = 50  # 50 * 0.2s = 10 seconds max wait


def _schedule_post_process(filepath, gltf_format):
    """Schedule GLB post-processing using a timer."""
    global _pending_post_process, _post_process_retries
    import sys

    print(f"KTX2 Extension: Scheduling post-process for {filepath} (format={gltf_format})")
    sys.stdout.flush()

    _pending_post_process = {
        'filepath': filepath,
        'gltf_format': gltf_format
    }
    _post_process_retries = 0  # Reset retry counter
    # Register timer to run after export completes
    try:
        bpy.app.timers.register(_timer_post_process, first_interval=0.5)
        print("KTX2 Extension: Timer registered successfully")
        sys.stdout.flush()
    except Exception as e:
        print(f"KTX2 Extension: Failed to register timer: {e}")
        sys.stdout.flush()
        import traceback
        traceback.print_exc()


def _timer_post_process():
    """Timer callback to post-process GLB/GLTF after export."""
    global _pending_post_process, _post_process_retries
    import sys
    import os
    import time

    print("KTX2 Extension: Timer callback invoked")
    sys.stdout.flush()

    if _pending_post_process is None:
        print("KTX2 Extension: No pending post-process, stopping timer")
        sys.stdout.flush()
        _post_process_retries = 0
        return None  # Stop timer

    filepath = _pending_post_process['filepath']
    gltf_format = _pending_post_process['gltf_format']

    # Check retry limit
    if _post_process_retries >= _MAX_POST_PROCESS_RETRIES:
        print(f"KTX2 Extension: Max retries ({_MAX_POST_PROCESS_RETRIES}) exceeded, giving up")
        sys.stdout.flush()
        _pending_post_process = None
        _post_process_retries = 0
        return None

    # Check if file exists
    if not os.path.exists(filepath):
        print(f"KTX2 Extension: File not found yet, retrying... ({_post_process_retries + 1}/{_MAX_POST_PROCESS_RETRIES})")
        sys.stdout.flush()
        _post_process_retries += 1
        return 0.2  # Try again in 0.2 seconds

    # Check if file is still being written by checking if size is stable
    try:
        size1 = os.path.getsize(filepath)
        time.sleep(0.05)  # Brief pause
        size2 = os.path.getsize(filepath)
        if size1 != size2:
            print(f"KTX2 Extension: File still being written, retrying... ({_post_process_retries + 1}/{_MAX_POST_PROCESS_RETRIES})")
            sys.stdout.flush()
            _post_process_retries += 1
            return 0.2
    except OSError:
        _post_process_retries += 1
        return 0.2

    # File is ready, clear pending state
    _pending_post_process = None
    _post_process_retries = 0

    print(f"KTX2 Extension: Timer triggered, processing {filepath}")
    sys.stdout.flush()

    try:
        if filepath.lower().endswith('.glb'):
            _post_process_glb_envmap(filepath, None)
        elif filepath.lower().endswith('.gltf'):
            _post_process_gltf_envmap(filepath, gltf_format)
    except Exception as e:
        print(f"KTX2 Extension: Failed to post-process for environment map: {e}")
        import traceback
        traceback.print_exc()

    return None  # Stop timer


def _post_process_glb_envmap(filepath, export_settings):
    """
    Post-process a GLB file to convert environment map data URI to bufferView.

    GLB format:
    - 12 byte header: magic (4), version (4), length (4)
    - JSON chunk: length (4), type "JSON" (4), json data (padded to 4 bytes)
    - Binary chunk: length (4), type "BIN\0" (4), binary data (padded to 4 bytes)
    """
    import json
    import base64
    import struct

    with open(filepath, 'rb') as f:
        glb_data = f.read()

    # Parse GLB header
    magic, version, total_length = struct.unpack('<III', glb_data[:12])
    if magic != 0x46546C67:  # 'glTF' in little-endian
        print("KTX2 Extension: Not a valid GLB file")
        return

    # Parse JSON chunk
    json_chunk_length, json_chunk_type = struct.unpack('<II', glb_data[12:20])
    if json_chunk_type != 0x4E4F534A:  # 'JSON' in little-endian
        print("KTX2 Extension: Invalid JSON chunk")
        return

    json_data = glb_data[20:20 + json_chunk_length].decode('utf-8').rstrip('\x00 ')
    gltf = json.loads(json_data)

    # Parse binary chunk (if exists)
    bin_chunk_start = 20 + json_chunk_length
    # Align to 4 bytes
    if bin_chunk_start % 4 != 0:
        bin_chunk_start += 4 - (bin_chunk_start % 4)

    binary_data = bytearray()
    if bin_chunk_start + 8 <= len(glb_data):
        bin_chunk_length, bin_chunk_type = struct.unpack('<II', glb_data[bin_chunk_start:bin_chunk_start + 8])
        if bin_chunk_type == 0x004E4942:  # 'BIN\0' in little-endian
            binary_data = bytearray(glb_data[bin_chunk_start + 8:bin_chunk_start + 8 + bin_chunk_length])

    # Find images with data URIs that are KTX2
    images = gltf.get('images', [])
    modified = False

    for i, image in enumerate(images):
        uri = image.get('uri', '')
        if isinstance(uri, str) and uri.startswith('data:image/ktx2;base64,'):
            # Extract base64 data
            b64_data = uri[len('data:image/ktx2;base64,'):]
            ktx2_bytes = base64.b64decode(b64_data)

            # Align binary buffer to 4 bytes before adding new data
            padding = (4 - len(binary_data) % 4) % 4
            if padding > 0:
                binary_data.extend(b'\x00' * padding)

            byte_offset = len(binary_data)
            binary_data.extend(ktx2_bytes)

            # Create or extend bufferViews
            if 'bufferViews' not in gltf:
                gltf['bufferViews'] = []

            buffer_view_index = len(gltf['bufferViews'])
            gltf['bufferViews'].append({
                'buffer': 0,
                'byteOffset': byte_offset,
                'byteLength': len(ktx2_bytes)
            })

            # Update image to use bufferView instead of URI
            del image['uri']
            image['bufferView'] = buffer_view_index
            image['mimeType'] = 'image/ktx2'

            modified = True

    if not modified:
        return

    # Update buffer length
    if 'buffers' not in gltf or len(gltf['buffers']) == 0:
        gltf['buffers'] = [{'byteLength': len(binary_data)}]
    else:
        gltf['buffers'][0]['byteLength'] = len(binary_data)

    # Rebuild GLB
    new_json = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    # Pad JSON to 4 bytes with spaces
    json_padding = (4 - len(new_json) % 4) % 4
    new_json += b' ' * json_padding

    # Pad binary to 4 bytes with zeros
    bin_padding = (4 - len(binary_data) % 4) % 4
    binary_data.extend(b'\x00' * bin_padding)

    # Calculate new total length
    new_total_length = 12 + 8 + len(new_json) + 8 + len(binary_data)

    # Build new GLB
    new_glb = bytearray()
    # Header
    new_glb.extend(struct.pack('<III', 0x46546C67, 2, new_total_length))
    # JSON chunk
    new_glb.extend(struct.pack('<II', len(new_json), 0x4E4F534A))
    new_glb.extend(new_json)
    # Binary chunk
    new_glb.extend(struct.pack('<II', len(binary_data), 0x004E4942))
    new_glb.extend(binary_data)

    # Write back
    with open(filepath, 'wb') as f:
        f.write(new_glb)

    print(f"KTX2 Extension: Successfully post-processed GLB, new size: {len(new_glb)} bytes")


def _post_process_gltf_envmap(filepath, gltf_format):
    """
    Post-process a GLTF file to convert environment map data URI to bufferView.

    Handles both:
    - GLTF_SEPARATE: JSON + separate .bin file
    - GLTF_EMBEDDED: JSON with base64-encoded buffer inline
    """
    import json
    import base64
    import os
    import sys

    print(f"KTX2 Extension: Post-processing GLTF file: {filepath}")
    sys.stdout.flush()

    with open(filepath, 'r', encoding='utf-8') as f:
        gltf = json.load(f)

    # Find images with data URIs that are KTX2
    images = gltf.get('images', [])
    modified = False
    ktx2_data_list = []  # Store data to append to buffer

    for i, image in enumerate(images):
        uri = image.get('uri', '')
        if isinstance(uri, str) and uri.startswith('data:image/ktx2;base64,'):
            # Extract base64 data
            b64_data = uri[len('data:image/ktx2;base64,'):]
            ktx2_bytes = base64.b64decode(b64_data)
            ktx2_data_list.append((i, image, ktx2_bytes))
            modified = True

    if not modified:
        print("KTX2 Extension: No KTX2 data URIs found to process")
        sys.stdout.flush()
        return

    # Get or create buffer
    buffers = gltf.get('buffers', [])

    # Determine if we have a separate .bin file or embedded buffer
    buffer_uri = buffers[0].get('uri', '') if buffers else ''
    is_embedded = not buffer_uri or buffer_uri.startswith('data:')

    if is_embedded:
        # GLTF_EMBEDDED: buffer is base64-encoded in the JSON
        print("KTX2 Extension: Processing embedded buffer format")
        sys.stdout.flush()

        # Decode existing buffer data (if any)
        if buffer_uri.startswith('data:'):
            # Extract base64 data from data URI
            # Format: data:application/octet-stream;base64,XXXXX
            comma_idx = buffer_uri.find(',')
            if comma_idx != -1:
                existing_b64 = buffer_uri[comma_idx + 1:]
                binary_data = bytearray(base64.b64decode(existing_b64))
            else:
                binary_data = bytearray()
        elif buffers and buffers[0].get('byteLength', 0) > 0:
            # Buffer exists but no data yet (shouldn't happen)
            binary_data = bytearray()
        else:
            # No existing buffer
            binary_data = bytearray()
            if not buffers:
                gltf['buffers'] = [{}]
                buffers = gltf['buffers']

        original_size = len(binary_data)

        # Process each KTX2 image
        if 'bufferViews' not in gltf:
            gltf['bufferViews'] = []

        for i, image, ktx2_bytes in ktx2_data_list:
            # Align binary buffer to 4 bytes before adding new data
            padding = (4 - len(binary_data) % 4) % 4
            if padding > 0:
                binary_data.extend(b'\x00' * padding)

            byte_offset = len(binary_data)
            binary_data.extend(ktx2_bytes)

            # Create bufferView
            buffer_view_index = len(gltf['bufferViews'])
            gltf['bufferViews'].append({
                'buffer': 0,
                'byteOffset': byte_offset,
                'byteLength': len(ktx2_bytes)
            })

            # Update image to use bufferView instead of URI
            del image['uri']
            image['bufferView'] = buffer_view_index
            image['mimeType'] = 'image/ktx2'
            sys.stdout.flush()

        # Update buffer with new base64-encoded data
        new_b64 = base64.b64encode(binary_data).decode('ascii')
        buffers[0]['uri'] = f"data:application/octet-stream;base64,{new_b64}"
        buffers[0]['byteLength'] = len(binary_data)

        # Write updated JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(gltf, f, separators=(',', ':'))

        sys.stdout.flush()

    else:
        # GLTF_SEPARATE: buffer is in a separate .bin file
        print("KTX2 Extension: Processing separate .bin file format")
        sys.stdout.flush()

        # Construct the path to the .bin file
        gltf_dir = os.path.dirname(filepath)
        bin_path = os.path.join(gltf_dir, buffer_uri)

        if not os.path.exists(bin_path):
            print(f"KTX2 Extension: Binary file not found: {bin_path}")
            sys.stdout.flush()
            return

        # Read existing binary data
        with open(bin_path, 'rb') as f:
            binary_data = bytearray(f.read())

        original_size = len(binary_data)

        # Process each KTX2 image
        if 'bufferViews' not in gltf:
            gltf['bufferViews'] = []

        for i, image, ktx2_bytes in ktx2_data_list:
            # Align binary buffer to 4 bytes before adding new data
            padding = (4 - len(binary_data) % 4) % 4
            if padding > 0:
                binary_data.extend(b'\x00' * padding)

            byte_offset = len(binary_data)
            binary_data.extend(ktx2_bytes)

            # Create bufferView
            buffer_view_index = len(gltf['bufferViews'])
            gltf['bufferViews'].append({
                'buffer': 0,
                'byteOffset': byte_offset,
                'byteLength': len(ktx2_bytes)
            })

            # Update image to use bufferView instead of URI
            del image['uri']
            image['bufferView'] = buffer_view_index
            image['mimeType'] = 'image/ktx2'
            sys.stdout.flush()

        # Update buffer length
        buffers[0]['byteLength'] = len(binary_data)

        # Write updated binary file
        with open(bin_path, 'wb') as f:
            f.write(binary_data)

        # Write updated JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(gltf, f, separators=(',', ':'))

        print(f"KTX2 Extension: Successfully post-processed GLTF")
        print(f"  Binary file grew from {original_size} to {len(binary_data)} bytes")
        print(f"  JSON updated: {filepath}")
        sys.stdout.flush()
