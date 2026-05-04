# Yunyun Faithful English Patch

A faithful English retranslation/restoration patch for **Yunyun Syndrome!? Rhythm Psychosis**, focused on preserving the Japanese source text's meaning, tone, references, internet-culture context, and character voice.

This project does not include or redistribute game files. You must supply your own lawful copy of the game. This project is unofficial and is not affiliated with, endorsed by, or sponsored by the developer, publisher, platform, or rightsholder.

The patcher replaces the shipped English locale with a faithful English script and UI translation.

This project is an independent English retranslation from the Japanese source text, with an explicit translation process designed to avoid bleed-through from the official English localization. The official English localization was not used as a base text, translation memory, drafting source, or revision source. Short or formulaic lines may still match other English renderings, including the official localization, where the Japanese source naturally leads to the same ordinary English phrasing.

Maintained by `qdenpa-receiver`.

## Using The Patcher

Download the release for your operating system and run it:

```bash
yunyun-faithful-english-patch
```

The patcher looks for common Steam install locations, including nearby `../Steam/steamapps/common/Yunyun_Syndrome/` and `../steamapps/common/Yunyun_Syndrome/` folders. You can also place the executable directly in the game root folder where `Yunyun_Syndrome.exe` is located.

The patcher validates the game layout, checks the target files, creates backups under `Yunyun_Syndrome_Data/.yunyun_faithful_english_patch_backups/`, and updates the English locale in place.

Useful options:

```bash
yunyun-faithful-english-patch --check
yunyun-faithful-english-patch --dry-run
yunyun-faithful-english-patch --restore
yunyun-faithful-english-patch --game-root /path/to/Yunyun_Syndrome
```

Use `--force` only when patching a known-compatible game build whose file hashes differ from the expected build.

## Platform Testing Status

The release executables are built by GitHub Actions. Windows patch and restore behavior has been live-tested. macOS builds are smoke-tested in CI but still need live game validation.

Back up your game files before patching.

## Build From Source

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Then run the patcher from the game root folder:

```bash
yunyun-faithful-english-patch
```

## Translation Maintenance

The extractor is included as a source tool for translation maintenance and is not packaged as a release executable:

```bash
python -m yunyun_faithful_english_patch.extract --game-root /path/to/game --out work/extracted
```

By default, the extractor writes shipped English rows, Japanese source rows, and local JSONL comparison reports against the committed English replacement translation. String-table JSONL rows include both Unity entry IDs and localization keys. Use `--locale en` or `--locale ja` to extract only one locale. Extractor output is local working data and is excluded from releases.

## Translation Feedback

Translation suggestions are collected through GitHub Discussions so they can be reviewed, labeled, and checked against the Japanese source.

Please read `TRANSLATION_FEEDBACK.md` before submitting wording suggestions, JP nuance corrections, proper-noun checks, typo reports, or runtime text reports. Use the [Translation Suggestions](https://github.com/qdenpa-receiver/yunyun-faithful-english-patch/discussions/categories/translation-suggestions) discussion category for ordinary translation feedback.

## Licensing

Code and build scripts are MIT licensed. Project-created replacement translation content is licensed under CC-BY-NC-SA-4.0 with the additional rightsholder permission included in this repository. See `LICENSE.md`, `RIGHTSHOLDER_PERMISSION.md`, and `NOTICE.md`.
