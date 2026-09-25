from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path


MOBILE_ROOT = Path(__file__).resolve().parents[1]
ANDROID_ROOT = MOBILE_ROOT / "android"
APP_ROOT = ANDROID_ROOT / "app"
GRADLE_FILE = APP_ROOT / "build.gradle.kts"
KEYSTORE_FILE = APP_ROOT / "upload-keystore.jks"
PROPERTIES_FILE = ANDROID_ROOT / "key.properties"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    if not GRADLE_FILE.exists():
        raise SystemExit(
            "Generated Android build file is missing. Run "
            "'flutter create . --platforms=android --org ai.chesscoach' first."
        )

    encoded = required_env("ANDROID_KEYSTORE_BASE64")
    store_password = required_env("ANDROID_KEYSTORE_PASSWORD")
    key_alias = required_env("ANDROID_KEY_ALIAS")
    key_password = required_env("ANDROID_KEY_PASSWORD")

    try:
        keystore_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SystemExit("ANDROID_KEYSTORE_BASE64 is not valid base64") from exc

    if not keystore_bytes:
        raise SystemExit("Decoded Android keystore is empty")

    KEYSTORE_FILE.write_bytes(keystore_bytes)
    KEYSTORE_FILE.chmod(0o600)

    PROPERTIES_FILE.write_text(
        "\n".join(
            [
                f"storePassword={store_password}",
                f"keyPassword={key_password}",
                f"keyAlias={key_alias}",
                "storeFile=upload-keystore.jks",
                "",
            ]
        ),
        encoding="utf-8",
    )
    PROPERTIES_FILE.chmod(0o600)

    content = GRADLE_FILE.read_text(encoding="utf-8")
    if "val keystoreProperties = Properties()" in content:
        raise SystemExit("Release signing appears to already be configured")

    android_marker = "android {"
    build_types_marker = "    buildTypes {"
    debug_signing = 'signingConfig = signingConfigs.getByName("debug")'

    if content.count(android_marker) != 1:
        raise SystemExit("Could not locate a unique android block in build.gradle.kts")
    if content.count(build_types_marker) != 1:
        raise SystemExit("Could not locate a unique buildTypes block in build.gradle.kts")
    if content.count(debug_signing) != 1:
        raise SystemExit(
            "Expected exactly one debug signing assignment in the generated release build type"
        )

    imports = (
        "import java.io.FileInputStream\n"
        "import java.util.Properties\n\n"
    )
    properties_block = (
        'val keystoreProperties = Properties()\n'
        'val keystorePropertiesFile = rootProject.file("key.properties")\n'
        "if (!keystorePropertiesFile.exists()) {\n"
        '    error("android/key.properties is required for release signing")\n'
        "}\n"
        "keystoreProperties.load(FileInputStream(keystorePropertiesFile))\n\n"
    )
    signing_block = (
        "    signingConfigs {\n"
        '        create("release") {\n'
        '            keyAlias = keystoreProperties.getProperty("keyAlias")\n'
        '            keyPassword = keystoreProperties.getProperty("keyPassword")\n'
        '            storeFile = keystoreProperties.getProperty("storeFile")?.let { file(it) }\n'
        '            storePassword = keystoreProperties.getProperty("storePassword")\n'
        "        }\n"
        "    }\n\n"
    )

    content = imports + content
    content = content.replace(android_marker, properties_block + android_marker, 1)
    content = content.replace(build_types_marker, signing_block + build_types_marker, 1)
    content = content.replace(
        debug_signing,
        'signingConfig = signingConfigs.getByName("release")',
        1,
    )

    GRADLE_FILE.write_text(content, encoding="utf-8")
    print("Android release signing configured without exposing secret values.")


if __name__ == "__main__":
    main()
