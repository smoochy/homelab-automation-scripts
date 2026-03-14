# Arr-Suite

[![README Style](https://img.shields.io/badge/README%20style-standard-2ea44f)](https://github.com/RichardLitt/standard-readme)

[![Buy me uptime](https://img.shields.io/badge/Buy%20me%20uptime%20%F0%9F%96%A5%EF%B8%8F-smoochy84-E9C46A?logo=buymeacoffee&logoColor=000000)](https://www.buymeacoffee.com/smoochy84)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-smoochy-7CC6FE?logo=ko-fi&logoColor=000000)](https://ko-fi.com/smoochy)

> A collection of task-focused automation scripts for self-hosted library operations, post-processing, and metadata-driven service workflows.

This repository groups small, focused utilities for environments built around
tools such as Radarr, SABnzbd, Tautulli, and related self-hosted services. The
scripts are designed to help with workflow automation, queue cleanup, tagging,
and other operational tasks that are easier to maintain as standalone helpers.

If these scripts save you time in your self-hosted setup, you can support
ongoing maintenance and documentation for a project I maintain in my spare time
via Ko-fi or Buy Me a Coffee.

## Table of Contents

- [Background](#background)
- [Available Scripts](#available-scripts)
- [Install](#install)
- [Usage](#usage)
- [Transparency](#transparency)
- [Maintainers](#maintainers)
- [Contributing](#contributing)
- [License](#license)

## Background

Self-hosted service stacks often need small helper scripts for post-processing,
tagging, queue handling, and related operational tasks. This repository
collects those utilities in one place and keeps each script documented in its
own folder.

## Available Scripts

### Radarr

- [Auto Tag and Deferred Cleanup for Watched Movies](./Radarr/Auto_Tag/)

### SABnzbd

- [ISO Extractor Post-Processing Script](./SABnzbd/extract_iso/)
- [Delete Items From History Scripts](./SABnzbd/delete_item_from_history/)

## Install

Clone the repository and then open the subdirectory for the script you want to
use.

```bash
git clone https://github.com/smoochy/Arr-Suite.git
cd Arr-Suite
```

Each script has its own README with tool-specific setup steps, dependencies,
usage details, and a script-level `CHANGELOG.md` for change tracking.

## Usage

Pick the relevant subdirectory and follow that script's README. The repository
root is only an index; the actual installation and runtime instructions live
next to each script.

## Transparency

The code, documentation, and related project materials in this repository were
created and refined with AI assistance. All generated output was reviewed and
adapted before publication.

## Maintainers

- [smoochy](https://github.com/smoochy)

## Contributing

Issues and pull requests are welcome. Keep new additions focused, documented,
and grouped under the relevant application directory.

## License

[MIT](./LICENSE) 2026 [smoochy](https://github.com/smoochy)
