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
KTX Tools Management

Handles downloading, extracting, and locating the KTX-Software command-line tools
for encoding and decoding KTX2 textures.
"""

import os
import sys
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path

# KTX-Software version to download
KTX_VERSION = "4.4.2"
COMPRESSONATOR_VERSION = "4.5.52"

# Base URL for downloading
GITHUB_BASE = f"https://github.com/KhronosGroup/KTX-Software/releases/download/v{KTX_VERSION}"
COMPRESSONATOR_BASE = f"https://github.com/GPUOpen-Tools/compressonator/releases/download/V{COMPRESSONATOR_VERSION}"
KTX2_MAGIC = bytes([0xAB, 0x4B, 0x54, 0x58, 0x20, 0x32, 0x30, 0xBB, 0x0D, 0x0A, 0x1A, 0x0A])

KTX2_SRGB_VKFORMAT_MAP = {
    131: 132,  # VK_FORMAT_BC1_RGB_UNORM_BLOCK -> VK_FORMAT_BC1_RGB_SRGB_BLOCK
    133: 134,  # VK_FORMAT_BC1_RGBA_UNORM_BLOCK -> VK_FORMAT_BC1_RGBA_SRGB_BLOCK
    135: 136,  # VK_FORMAT_BC2_UNORM_BLOCK -> VK_FORMAT_BC2_SRGB_BLOCK
    137: 138,  # VK_FORMAT_BC3_UNORM_BLOCK -> VK_FORMAT_BC3_SRGB_BLOCK
    145: 146,  # VK_FORMAT_BC7_UNORM_BLOCK -> VK_FORMAT_BC7_SRGB_BLOCK
}

KHR_DF_TRANSFER_SRGB = 2


def get_platform_info():
    """
    Detect the current platform and architecture.

    Returns:
        tuple: (os_name, arch) e.g. ('Linux', 'x86_64'), ('Windows', 'x64'), ('Darwin', 'arm64')
    """
    os_name = platform.system()  # 'Linux', 'Windows', 'Darwin'
    machine = platform.machine().lower()

    # Normalize architecture names
    if machine in ('x86_64', 'amd64'):
        arch = 'x86_64'
    elif machine in ('aarch64', 'arm64'):
        arch = 'arm64'
    else:
        arch = machine

    return os_name, arch


def get_download_info():
    """
    Get the download URL and archive type for the current platform.

    Returns:
        tuple: (url, archive_type, extract_subdir) or (None, None, None) if unsupported
    """
    os_name, arch = get_platform_info()

    # Use GitHub releases for more reliable downloads
    github_base = f"https://github.com/KhronosGroup/KTX-Software/releases/download/v{KTX_VERSION}"

    if os_name == 'Linux':
        if arch == 'x86_64':
            filename = f"KTX-Software-{KTX_VERSION}-Linux-x86_64.tar.bz2"
        elif arch == 'arm64':
            filename = f"KTX-Software-{KTX_VERSION}-Linux-arm64.tar.bz2"
        else:
            return None, None, None
        return f"{github_base}/{filename}", 'tar.bz2', f"KTX-Software-{KTX_VERSION}-Linux-{arch}"

    elif os_name == 'Windows':
        # Windows uses installer (.exe), need 7-Zip to extract
        if arch == 'x86_64':
            filename = f"KTX-Software-{KTX_VERSION}-Windows-x64.exe"
        elif arch == 'arm64':
            filename = f"KTX-Software-{KTX_VERSION}-Windows-arm64.exe"
        else:
            return None, None, None
        return f"{github_base}/{filename}", 'exe', None

    elif os_name == 'Darwin':
        if arch == 'x86_64':
            filename = f"KTX-Software-{KTX_VERSION}-Darwin-x86_64.pkg"
        elif arch == 'arm64':
            filename = f"KTX-Software-{KTX_VERSION}-Darwin-arm64.pkg"
        else:
            return None, None, None
        return f"{github_base}/{filename}", 'pkg', None

    return None, None, None


def get_compressonator_download_info():
    """
    Get the download URL and archive type for CompressonatorCLI on this platform.

    Returns:
        tuple: (url, archive_type) or (None, None) if unsupported.
    """
    os_name, arch = get_platform_info()

    if arch != 'x86_64':
        return None, None

    if os_name == 'Windows':
        filename = f"compressonatorcli-{COMPRESSONATOR_VERSION}-win64.zip"
        return f"{COMPRESSONATOR_BASE}/{filename}", 'zip'

    if os_name == 'Linux':
        filename = f"compressonatorcli-{COMPRESSONATOR_VERSION}-Linux.tar.gz"
        return f"{COMPRESSONATOR_BASE}/{filename}", 'tar.gz'

    return None, None


def get_tools_directory():
    """
    Get the directory where KTX tools should be stored.

    Returns:
        Path: Directory path for storing tools
    """
    # Store in the addon's directory
    addon_dir = Path(__file__).parent
    tools_dir = addon_dir / "bin"
    return tools_dir


def get_compressonator_directory():
    """
    Get the directory where CompressonatorCLI should be stored.

    Returns:
        Path: Directory path for the extracted CompressonatorCLI bundle
    """
    return get_tools_directory() / "compressonator"


def find_executable_in_directory(root_dir, candidate_names):
    """Search a directory tree for the first matching executable."""
    root_dir = Path(root_dir)
    if not root_dir.exists():
        return None

    for candidate_name in candidate_names:
        for match in root_dir.rglob(candidate_name):
            if match.is_file() and os.access(match, os.X_OK):
                return match

    return None


def get_tool_path(tool_name):
    """
    Get the full path to a KTX tool executable.

    Args:
        tool_name: Name of the tool ('toktx', 'ktx', etc.)

    Returns:
        Path: Full path to the executable, or None if not found
    """
    tools_dir = get_tools_directory()
    os_name, _ = get_platform_info()

    if os_name == 'Windows':
        exe_name = f"{tool_name}.exe"
    else:
        exe_name = tool_name

    tool_path = tools_dir / exe_name

    if tool_path.exists() and os.access(tool_path, os.X_OK):
        return tool_path

    return None


def are_tools_installed():
    """
    Check if the required KTX tools are installed.

    Returns:
        bool: True if tools are available
    """
    toktx = get_tool_path('toktx')
    return toktx is not None


def get_compressonator_path():
    """
    Get the full path to the Compressonator CLI executable.

    Returns:
        Path: Full path to the executable, or None if not found
    """
    tools_dir = get_tools_directory()
    compressonator_dir = get_compressonator_directory()
    os_name, _ = get_platform_info()

    candidate_paths = []

    if os_name == 'Windows':
        candidate_names = ('CompressonatorCLI.exe', 'compressonatorcli.exe')
        program_files = os.environ.get('ProgramFiles', r'C:\Program Files')
        candidate_paths.extend([
            Path(program_files) / 'Compressonator' / 'CompressonatorCLI.exe',
            Path(program_files) / 'Compressonator' / 'bin' / 'CLI' / 'CompressonatorCLI.exe',
            tools_dir / 'CompressonatorCLI.exe',
            compressonator_dir / 'CompressonatorCLI.exe',
            compressonator_dir / 'bin' / 'CLI' / 'CompressonatorCLI.exe',
        ])
    else:
        candidate_names = ('CompressonatorCLI', 'compressonatorcli')
        candidate_paths.extend([
            tools_dir / 'CompressonatorCLI',
            compressonator_dir / 'CompressonatorCLI',
            compressonator_dir / 'bin' / 'CLI' / 'CompressonatorCLI',
        ])

    for candidate in candidate_paths:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate

    local_match = find_executable_in_directory(compressonator_dir, candidate_names)
    if local_match:
        return local_match

    for candidate_name in candidate_names:
        found = shutil.which(candidate_name)
        if found:
            return Path(found)

    return None


def are_bcn_tools_installed():
    """Check if the BCn encoder backend is available."""
    return get_compressonator_path() is not None


def download_file(url, dest_path, progress_callback=None):
    """
    Download a file from URL to destination path.

    Args:
        url: URL to download from
        dest_path: Destination file path
        progress_callback: Optional callback(bytes_downloaded, total_bytes)

    Returns:
        bool: True if successful
    """
    import urllib.request
    import urllib.error
    import ssl

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ssl_context = ssl.create_default_context()
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': '*/*',
        }
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request, timeout=120, context=ssl_context)

        content_type = response.getheader('Content-Type', '')
        if 'text/html' in content_type.lower():
            print(f"Received HTML instead of binary (Content-Type: {content_type})")
            response.close()
            return False

        total_size = response.getheader('Content-Length')
        total_size = int(total_size) if total_size else None

        print(f"Downloading {total_size // 1024 // 1024 if total_size else '?'}MB...")

        downloaded = 0
        chunk_size = 65536

        with open(dest_path, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size:
                    progress_callback(downloaded, total_size)

        response.close()

        # Verify we got a valid file (not HTML)
        with open(dest_path, 'rb') as f:
            header = f.read(16)
            if header.startswith(b'<!') or header.startswith(b'<html') or header.startswith(b'<HTML'):
                print("Downloaded file appears to be HTML, not the expected archive")
                return False
            if str(dest_path).endswith('.tar.bz2') and not header.startswith(b'BZ'):
                print(f"Downloaded file does not appear to be bzip2 (header: {header[:4]})")
                return False
            if str(dest_path).endswith('.tar.gz') and header[:2] != b'\x1f\x8b':
                print(f"Downloaded file does not appear to be gzip (header: {header[:4]})")
                return False
            if str(dest_path).endswith('.zip') and header[:2] != b'PK':
                print(f"Downloaded file does not appear to be zip (header: {header[:4]})")
                return False

        print(f"Download complete: {downloaded // 1024}KB")
        return True

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        return False

    except (urllib.error.URLError, OSError) as e:
        print(f"Download failed: {e}")
        return False


def get_seven_zip_path():
    """Get a usable 7-Zip executable path on Windows, or None if unavailable."""
    seven_zip_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        "7z",
    ]

    for path in seven_zip_paths:
        try:
            result = subprocess.run([path, '--help'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return path
        except (subprocess.SubprocessError, FileNotFoundError):
            continue

    return None


def extract_linux_archive(archive_path, tools_dir):
    """Extract tools from Linux tar.bz2 archive."""
    import tarfile

    tools_dir.mkdir(parents=True, exist_ok=True)

    # Create lib subdirectory for shared libraries
    lib_dir = tools_dir / 'lib'
    lib_dir.mkdir(parents=True, exist_ok=True)

    extracted_libs = []

    with tarfile.open(archive_path, 'r:bz2') as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue

            filename = os.path.basename(member.name)

            # Extract executables from bin directory
            if '/bin/' in member.name:
                if filename in ('toktx', 'ktx', 'ktxsc', 'ktxinfo'):
                    tar.extract(member, path=tools_dir.parent)
                    extracted_path = tools_dir.parent / member.name
                    dest_path = tools_dir / filename
                    shutil.move(str(extracted_path), str(dest_path))
                    os.chmod(dest_path, 0o755)
                    print(f"[KTX2] Extracted: {filename}")

            # Extract shared libraries from lib directory
            elif '/lib/' in member.name:
                if filename.startswith('libktx') and '.so' in filename:
                    tar.extract(member, path=tools_dir.parent)
                    extracted_path = tools_dir.parent / member.name
                    dest_path = lib_dir / filename
                    shutil.move(str(extracted_path), str(dest_path))
                    extracted_libs.append(filename)
                    print(f"[KTX2] Extracted library: {filename}")

    # Create symlinks for versioned libraries
    # e.g., libktx.so.4.4.2 -> libktx.so.4 -> libktx.so
    for lib_file in extracted_libs:
        lib_path = lib_dir / lib_file

        # Parse version from filename like libktx.so.4.4.2
        if '.so.' in lib_file:
            base_name = lib_file.split('.so.')[0]  # e.g., 'libktx'
            version = lib_file.split('.so.')[1]     # e.g., '4.4.2'

            # Create major version symlink (libktx.so.4 -> libktx.so.4.4.2)
            major_version = version.split('.')[0]
            major_symlink = lib_dir / f"{base_name}.so.{major_version}"
            if not major_symlink.exists():
                os.symlink(lib_file, major_symlink)
                print(f"[KTX2] Created symlink: {major_symlink.name} -> {lib_file}")

            # Create base symlink (libktx.so -> libktx.so.4.4.2)
            base_symlink = lib_dir / f"{base_name}.so"
            if not base_symlink.exists():
                os.symlink(lib_file, base_symlink)
                print(f"[KTX2] Created symlink: {base_symlink.name} -> {lib_file}")

    # Clean up extracted directories
    for item in tools_dir.parent.iterdir():
        if item.is_dir() and item.name.startswith('KTX-Software'):
            shutil.rmtree(item, ignore_errors=True)

    return True


def extract_windows_installer(installer_path, tools_dir):
    """
    Extract tools from Windows installer.

    The Windows .exe is an NSIS installer. We can extract it using 7z or
    by running it silently, but that's complex. Instead, we'll try to
    use the GitHub release assets which might have a zip.

    For now, we'll attempt to use 7z if available, otherwise provide instructions.
    """
    tools_dir.mkdir(parents=True, exist_ok=True)

    seven_zip = get_seven_zip_path()

    if seven_zip:
        # Extract using 7z
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(
                    [seven_zip, 'x', str(installer_path), f'-o{tmpdir}', '-y'],
                    capture_output=True,
                    timeout=120
                )

                # Find executables and DLLs
                for root, dirs, files in os.walk(tmpdir):
                    for filename in files:
                        if filename in ('toktx.exe', 'ktx.exe', 'ktxsc.exe', 'ktxinfo.exe'):
                            src = Path(root) / filename
                            dst = tools_dir / filename
                            shutil.copy2(src, dst)
                        elif filename.lower().endswith('.dll'):
                            src = Path(root) / filename
                            dst = tools_dir / filename
                            shutil.copy2(src, dst)

                return (tools_dir / 'toktx.exe').exists()
            except subprocess.SubprocessError:
                pass

    # Fallback: Try running installer silently (not ideal)
    # For better UX, we should provide manual instructions
    return False


def extract_compressonator_windows_archive(archive_path, target_dir):
    """Extract the Windows CompressonatorCLI archive into the target directory."""
    import zipfile

    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(archive_path, 'r') as archive:
            archive.extractall(path=target_dir)
    except zipfile.BadZipFile as e:
        return False, f"Invalid CompressonatorCLI zip archive: {e}"
    except OSError as e:
        return False, f"Failed to extract CompressonatorCLI: {e}"

    exe_names = ('CompressonatorCLI.exe', 'compressonatorcli.exe')
    if not find_executable_in_directory(target_dir, exe_names):
        return False, "CompressonatorCLI was extracted but the executable could not be found."

    return True, None


def extract_compressonator_linux_archive(archive_path, target_dir):
    """Extract the full CompressonatorCLI Linux bundle into the target directory."""
    import tarfile

    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(path=target_dir)

    for binary_name in ('CompressonatorCLI', 'compressonatorcli'):
        for match in target_dir.rglob(binary_name):
            try:
                os.chmod(match, 0o755)
            except OSError:
                pass

    exe_names = ('CompressonatorCLI', 'compressonatorcli')
    if not find_executable_in_directory(target_dir, exe_names):
        return False, "CompressonatorCLI was extracted but the executable could not be found."

    return True, None


def extract_macos_package(pkg_path, tools_dir):
    """Extract tools from macOS .pkg file."""
    tools_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        try:
            # Expand the pkg
            subprocess.run(
                ['pkgutil', '--expand', str(pkg_path), str(tmpdir / 'expanded')],
                capture_output=True,
                check=True,
                timeout=60
            )

            # Find and extract the payload
            payload_path = tmpdir / 'expanded' / 'ktx-tools.pkg' / 'Payload'
            if not payload_path.exists():
                # Try alternative structure
                for p in (tmpdir / 'expanded').rglob('Payload'):
                    payload_path = p
                    break

            if payload_path.exists():
                # Extract payload (it's a cpio archive, possibly gzipped)
                extract_dir = tmpdir / 'extracted'
                extract_dir.mkdir()

                # Try gunzip + cpio
                try:
                    with subprocess.Popen(
                        ['gunzip', '-c', str(payload_path)],
                        stdout=subprocess.PIPE
                    ) as gunzip:
                        subprocess.run(
                            ['cpio', '-id'],
                            stdin=gunzip.stdout,
                            cwd=str(extract_dir),
                            capture_output=True,
                            timeout=60
                        )
                except FileNotFoundError:
                    # gunzip not available, try with Python gzip
                    import gzip
                    with gzip.open(payload_path, 'rb') as f:
                        # This is more complex, skip for now
                        pass

                # Find and copy tools
                for root, dirs, files in os.walk(extract_dir):
                    for filename in files:
                        if filename in ('toktx', 'ktx', 'ktxsc', 'ktxinfo'):
                            src = Path(root) / filename
                            dst = tools_dir / filename
                            shutil.copy2(src, dst)
                            os.chmod(dst, 0o755)

                return (tools_dir / 'toktx').exists()

        except subprocess.SubprocessError as e:
            print(f"Failed to extract macOS package: {e}")

    return False


def install_tools(progress_callback=None):
    """
    Download and install KTX tools for the current platform.

    Args:
        progress_callback: Optional callback(status_message, progress_percent)

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    os_name, arch = get_platform_info()
    url, archive_type, _ = get_download_info()

    if url is None:
        return False, f"Unsupported platform: {os_name} {arch}"

    tools_dir = get_tools_directory()

    # Create temp directory for download
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        archive_path = tmpdir / f"ktx_tools.{archive_type}"

        # Download
        if progress_callback:
            progress_callback("Downloading KTX tools...", 0)

        def download_progress(downloaded, total):
            if progress_callback:
                percent = int(downloaded / total * 50)  # Download is 0-50%
                progress_callback(f"Downloading... {downloaded // 1024 // 1024}MB", percent)

        if not download_file(url, archive_path, download_progress):
            return False, "Failed to download KTX tools. Check your internet connection."

        # Extract
        if progress_callback:
            progress_callback("Extracting tools...", 50)

        try:
            if archive_type == 'tar.bz2':
                success = extract_linux_archive(archive_path, tools_dir)
            elif archive_type == 'exe':
                success = extract_windows_installer(archive_path, tools_dir)
            elif archive_type == 'pkg':
                success = extract_macos_package(archive_path, tools_dir)
            else:
                return False, f"Unknown archive type: {archive_type}"

            if not success:
                return False, "Failed to extract KTX tools from archive."

        except Exception as e:
            return False, f"Extraction failed: {str(e)}"

    # Verify installation
    if progress_callback:
        progress_callback("Verifying installation...", 90)

    if not are_tools_installed():
        return False, "Tools were extracted but verification failed."

    if progress_callback:
        progress_callback("Installation complete!", 100)

    return True, None


def install_compressonator(progress_callback=None):
    """
    Download and install CompressonatorCLI for BCn encoding.

    Args:
        progress_callback: Optional callback(status_message, progress_percent)

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    os_name, arch = get_platform_info()
    url, archive_type = get_compressonator_download_info()

    if url is None:
        return False, f"Automatic CompressonatorCLI download is not supported on {os_name} {arch}."

    target_dir = get_compressonator_directory()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        archive_path = tmpdir / f"compressonator.{archive_type}"

        if progress_callback:
            progress_callback("Downloading BCn tools...", 0)

        def download_progress(downloaded, total):
            if progress_callback:
                percent = int(downloaded / total * 60)
                progress_callback(f"Downloading... {downloaded // 1024 // 1024}MB", percent)

        if not download_file(url, archive_path, download_progress):
            return False, "Failed to download CompressonatorCLI. Check your internet connection."

        if progress_callback:
            progress_callback("Extracting BCn tools...", 60)

        try:
            if archive_type == 'zip':
                success, error = extract_compressonator_windows_archive(archive_path, target_dir)
            elif archive_type == 'tar.gz':
                success, error = extract_compressonator_linux_archive(archive_path, target_dir)
            else:
                return False, f"Unknown CompressonatorCLI archive type: {archive_type}"
        except Exception as e:
            return False, f"Extraction failed: {str(e)}"

        if not success:
            return False, error

    if progress_callback:
        progress_callback("Verifying BCn tools...", 90)

    if not are_bcn_tools_installed():
        return False, "CompressonatorCLI was extracted but verification failed."

    if progress_callback:
        progress_callback("BCn tools installed!", 100)

    return True, None


def get_tool_environment():
    """
    Get environment variables for running KTX tools.

    Sets LD_LIBRARY_PATH (Linux) or PATH (Windows) to include the lib directory.
    """
    env = os.environ.copy()
    tools_dir = get_tools_directory()
    lib_dir = tools_dir / 'lib'

    os_name, _ = get_platform_info()

    if os_name == 'Linux':
        # Add lib directory to LD_LIBRARY_PATH
        current_ld_path = env.get('LD_LIBRARY_PATH', '')
        if current_ld_path:
            env['LD_LIBRARY_PATH'] = f"{lib_dir}{os.pathsep}{current_ld_path}"
        else:
            env['LD_LIBRARY_PATH'] = str(lib_dir)
    elif os_name == 'Windows':
        # Add tools and lib directories to PATH for DLLs
        current_path = env.get('PATH', '')
        env['PATH'] = f"{tools_dir}{os.pathsep}{lib_dir}{os.pathsep}{current_path}"
    elif os_name == 'Darwin':
        # Add lib directory to DYLD_LIBRARY_PATH
        current_dyld_path = env.get('DYLD_LIBRARY_PATH', '')
        if current_dyld_path:
            env['DYLD_LIBRARY_PATH'] = f"{lib_dir}{os.pathsep}{current_dyld_path}"
        else:
            env['DYLD_LIBRARY_PATH'] = str(lib_dir)

    return env


def get_compressonator_environment(cli_path):
    """
    Get environment variables for running the Compressonator CLI.

    The CLI expects its support DLLs/plugins to be discoverable relative to the
    executable directory.
    """
    env = os.environ.copy()
    cli_dir_path = Path(cli_path).parent
    search_dirs = [
        str(cli_dir_path),
        str(cli_dir_path.parent),
        str(cli_dir_path / 'plugins'),
        str(cli_dir_path.parent / 'plugins'),
        str(cli_dir_path / 'lib'),
        str(cli_dir_path.parent / 'lib'),
    ]
    search_dirs = [path for path in search_dirs if Path(path).exists()]
    current_path = env.get('PATH', '')
    combined_path = os.pathsep.join(search_dirs + ([current_path] if current_path else []))
    env['PATH'] = combined_path

    current_ld_path = env.get('LD_LIBRARY_PATH', '')
    env['LD_LIBRARY_PATH'] = os.pathsep.join(search_dirs + ([current_ld_path] if current_ld_path else []))

    current_dyld_path = env.get('DYLD_LIBRARY_PATH', '')
    env['DYLD_LIBRARY_PATH'] = os.pathsep.join(search_dirs + ([current_dyld_path] if current_dyld_path else []))
    return env


def build_toktx_command(toktx_path, input_path, output_path, options=None):
    """Build the toktx command for a single encode operation."""
    options = options or {}
    cmd = [str(toktx_path)]

    target_format = options.get('target_format', 'BASISU')

    if target_format == 'ASTC':
        cmd.extend(['--encode', 'astc'])
        block_size = options.get('astc_block_size', '6x6')
        cmd.extend(['--astc_blk_d', block_size])
        cmd.extend(['--astc_quality', 'medium'])
        compression = options.get('compression', 3)
        cmd.extend(['--zcmp', str(compression)])
    else:
        fmt = options.get('format', 'ETC1S')
        if fmt == 'UASTC':
            cmd.extend(['--encode', 'uastc'])
            quality = options.get('quality', 2)
            cmd.extend(['--uastc_quality', str(quality)])
            compression = options.get('compression', 3)
            cmd.extend(['--zcmp', str(compression)])
        else:
            cmd.extend(['--encode', 'etc1s'])
            quality = options.get('quality', 128)
            cmd.extend(['--qlevel', str(quality)])
            compression = options.get('compression', 1)
            cmd.extend(['--clevel', str(compression)])

    oetf = options.get('oetf', 'srgb')
    cmd.extend(['--assign_oetf', oetf])

    target_type = options.get('target_type', 'RGBA')
    cmd.extend(['--target_type', target_type])

    scale = options.get('scale', 1.0)
    cmd.extend(['--scale', str(scale)])

    if options.get('mipmaps', False):
        cmd.append('--genmipmap')

    cmd.append(str(output_path))
    cmd.append(str(input_path))
    return cmd


def build_compressonator_command(cli_path, input_path, output_path, options=None):
    """Build the Compressonator CLI command for BCn encoding."""
    options = options or {}
    bc_format = options.get('bc_format', 'BC7')

    cmd = [
        str(cli_path),
        '-fd', bc_format,
        '-EncodeWith', 'CPU',
        '-silent',
    ]

    if options.get('mipmaps', False):
        cmd.extend(['-mipsize', '1'])
    else:
        cmd.append('-nomipmap')

    cmd.append(str(input_path))
    cmd.append(str(output_path))
    return cmd


def is_ktx2_bytes(data):
    """Return True when the byte string begins with the KTX2 file magic."""
    return data[:len(KTX2_MAGIC)] == KTX2_MAGIC


def is_ktx2_file(path):
    """Return True when the given file appears to be a KTX2 container."""
    try:
        with open(path, 'rb') as f:
            return is_ktx2_bytes(f.read(len(KTX2_MAGIC)))
    except OSError:
        return False


def patch_ktx2_srgb_metadata(path):
    """
    Update a KTX2 file to use the sRGB vkFormat and DFD transfer function.

    Compressonator's BCn CPU path emits valid KTX2, but does not tag BC1/3/7
    output as sRGB even when the source texture should be sampled as sRGB.
    """
    path = Path(path)
    data = bytearray(path.read_bytes())
    if not is_ktx2_bytes(data):
        return False, "Not a KTX2 file."

    if len(data) < 56:
        return False, "KTX2 header is truncated."

    vk_format = int.from_bytes(data[12:16], 'little')
    srgb_vk_format = KTX2_SRGB_VKFORMAT_MAP.get(vk_format)
    if srgb_vk_format is None:
        return False, f"No sRGB vkFormat mapping for {vk_format}."

    dfd_offset = int.from_bytes(data[48:52], 'little')
    dfd_length = int.from_bytes(data[52:56], 'little')
    descriptor_block_offset = dfd_offset + 4
    transfer_offset = descriptor_block_offset + 10
    if dfd_offset <= 0 or dfd_length < 16 or transfer_offset >= len(data):
        return False, "KTX2 DFD block is missing or truncated."

    data[12:16] = int(srgb_vk_format).to_bytes(4, 'little')
    data[transfer_offset] = KHR_DF_TRANSFER_SRGB
    path.write_bytes(data)
    return True, None


def run_toktx(input_path, output_path, options=None):
    """
    Run the toktx tool to convert an image to KTX2.

    Args:
        input_path: Path to input image (PNG, JPEG, etc.)
        output_path: Path for output KTX2 file
        options: Dict of options:
            - target_format: 'BASISU' or 'ASTC'
            - format: 'ETC1S' or 'UASTC' (for BASISU)
            - quality: 1-255 for ETC1S, 0-4 for UASTC
            - compression: 0-5 for ETC1S, 1-22 for UASTC
            - mipmaps: bool
            - astc_block_size: '4x4', '5x5', '6x6', '8x8' (for ASTC)
            - oetf: Transfer function (linear|srgb)
            - target_type: Target type (R, RG, RGB, RGBA)

    Returns:
        tuple: (success: bool, error_message: str or None)

    Notes on target formats:
        - BASISU: Basis Universal (ETC1S or UASTC) - universal, transcodes at runtime
                  to any GPU format (BC7, ASTC, ETC2, etc.)
        - ASTC: Native ASTC format - direct GPU upload on ASTC-capable hardware
                (mobile devices, Apple Silicon). No transcoding needed.
    """
    toktx_path = get_tool_path('toktx')
    if not toktx_path:
        return False, "toktx tool not found. Please install KTX tools first."

    cmd = build_toktx_command(toktx_path, input_path, output_path, options)

    try:
        env = get_tool_environment()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )

        if result.returncode != 0:
            return False, f"toktx failed: {result.stderr}"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "toktx timed out"
    except Exception as e:
        return False, f"Failed to run toktx: {str(e)}"


def run_compressonator(input_path, output_path, options=None):
    """
    Run the Compressonator CLI to encode a source image into BCn KTX2.
    """
    cli_path = get_compressonator_path()
    if not cli_path:
        return False, "CompressonatorCLI not found. Install it and make sure it is in PATH or the add-on bin folder."

    cmd = build_compressonator_command(cli_path, input_path, output_path, options)

    try:
        env = get_compressonator_environment(cli_path)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env
        )

        if result.returncode != 0:
            return False, f"CompressonatorCLI failed: {result.stderr}"

        if options and options.get('oetf') == 'srgb':
            patched, patch_error = patch_ktx2_srgb_metadata(output_path)
            if not patched:
                return False, f"CompressonatorCLI produced BCn data but sRGB metadata patch failed: {patch_error}"

        if not is_ktx2_file(output_path):
            return False, "CompressonatorCLI did not produce a valid KTX2 file."

        return True, None

    except subprocess.TimeoutExpired:
        return False, "CompressonatorCLI timed out"
    except Exception as e:
        return False, f"Failed to run CompressonatorCLI: {str(e)}"


def run_encoder(input_path, output_path, options=None):
    """
    Run the appropriate encoder backend for the requested target format.
    """
    options = options or {}
    if options.get('target_format') == 'BCN':
        return run_compressonator(input_path, output_path, options)
    return run_toktx(input_path, output_path, options)


def run_ktx_extract(input_path, output_path):
    """
    Run the ktx tool to extract/transcode a KTX2 file to PNG.

    Args:
        input_path: Path to input KTX2 file
        output_path: Path for output PNG file

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    ktx_path = get_tool_path('ktx')
    if not ktx_path:
        return False, "ktx tool not found. Please install KTX tools first."

    cmd = [
        str(ktx_path),
        'extract',
        str(input_path),
        str(output_path)
    ]

    try:
        env = get_tool_environment()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=120
        )

        if result.returncode != 0:
            return False, f"ktx extract failed: {result.stderr}"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "ktx extract timed out"
    except Exception as e:
        return False, f"Failed to run ktx: {str(e)}"
