# Portfolio Check

A small, dependency-free Python command-line tool for checking portfolio export manifests before publishing. Built by [Paxerr](https://paxerr.com) as a companion to our [portfolio publishing checklist](https://github.com/PaxerrOfficial/PaxerrOfficial/blob/main/guides/portfolio-publishing-checklist.md).

It catches missing files, changed SHA-256 hashes, duplicate source/export paths, missing review flags and invalid recorded dimensions. It reads local files only: no uploads, network requests, analytics or automatic edits.

## Quick start

Requires Python 3.10 or newer. Clone this repository; no package installation is needed.

```sh
git clone https://github.com/PaxerrOfficial/portfolio-check.git
cd portfolio-check
python portfolio_check.py hash /path/to/project/original.webm
python portfolio_check.py hash /path/to/project/exports/portrait.mp4
python portfolio_check.py check /path/to/project/manifest.json
```

On Windows, use `py` instead of `python` if that is your Python launcher. Quote paths containing spaces.

Keep the manifest alongside your project assets. Paths inside it must use forward slashes, be relative to the manifest directory, and resolve inside that directory. Originals and exports must be distinct files. Replace the hash placeholders with the output of `hash`; set `reviewed` to `true` only after reviewing the entire export.

```json
{
  "project": "Example project",
  "source": {
    "file": "original.webm",
    "sha256": "REPLACE_WITH_SOURCE_HASH"
  },
  "exports": [
    {
      "file": "exports/portrait.mp4",
      "sha256": "REPLACE_WITH_EXPORT_HASH",
      "width": 1080,
      "height": 1350,
      "reviewed": false
    }
  ]
}
```

The example is deliberately incomplete: it fails until real files, hashes and review results are supplied. Additional fields such as `caseStudyUrl` are allowed and ignored.

For build scripts or other tooling:

```sh
python portfolio_check.py check /path/to/project/manifest.json --json
```

Exit codes: **0** checks passed; **1** manifest/assets need attention; **2** invalid command or unreadable/invalid input. JSON mode returns `ok` and an `issues` array for manifest results.

## What a pass means

Only these mechanical checks passed. The tool does **not** inspect image/video frames, measure actual media dimensions, detect contact information, establish ownership or client permission, validate marketing claims, check current platform rules, or confirm publication. Recorded dimensions and the review flag are human assertions. Hashes identify bytes; they do not establish rights or approval. A file can also change after a check: check the exact exports immediately before upload.

Keep private client assets, credentials and session URLs out of public repositories. This repository contains only original tool code and tests using fictional text fixtures.

## Development

```sh
python -m unittest -v
```

Tests create temporary fictional files and cover hash drift, source preservation, duplicate paths, invalid input, path escape, symlinks (when supported), review flags and CLI exit codes. No external services are required.

MIT licensed. Bug reports and focused fixes are welcome.
