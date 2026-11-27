from pathlib import Path

from setuptools import find_namespace_packages, setup

setup(
    name="cli-anything-xcide",
    version="1.0.0",
    description="无需 MCP 的炫彩 IDE 与炫语言本地命令行工具",
    long_description=(Path(__file__).parent / "cli_anything/xcide/README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(include=["cli_anything.*"], exclude=["cli_anything.xcide.skills.*"]),
    package_data={
        "cli_anything.xcide": ["skills/*.md", "skills/*.html", "skills/references/xc-suite/**/*.md",
                               "skills/references/xc-suite/**/*.html", "skills/references/xc-suite/SOURCE.json",
                               "skills/references/xc-suite/scripts/xc_modules.py", "README.md", "README.html",
                               "AI_CALLING.md", "AI_CALLING.html", "tests/TEST.md", "tests/TEST.html",
                               "IDE_COMPAT.md", "IDE_COMPAT.html",
                               "native/*.cpp", "native/*.h", "examples/*"],
    },
    exclude_package_data={"": ["**/xc-modules/catalog.md", "**/xc-modules/catalog.json", "**/xc-modules/api.jsonl"]},
    install_requires=["click>=8.1", "filelock>=3.12", "prompt-toolkit>=3.0"],
    extras_require={"test": ["pytest>=8.0", "Pillow>=10.0"], "automation": ["Pillow>=10.0"]},
    entry_points={"console_scripts": ["cli-anything-xcide=cli_anything.xcide.xcide_cli:main"]},
    python_requires=">=3.10",
)
