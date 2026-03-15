# homelab-automation-scripts

[![README Style](https://img.shields.io/badge/README%20style-standard-2ea44f)](https://github.com/RichardLitt/standard-readme)

[![Buy me uptime](https://img.shields.io/badge/Buy%20me%20uptime%20%F0%9F%96%A5%EF%B8%8F-smoochy84-E9C46A?logo=buymeacoffee&logoColor=000000)](https://www.buymeacoffee.com/smoochy84)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-smoochy-7CC6FE?logo=ko-fi&logoColor=000000)](https://ko-fi.com/smoochy)

> Self-hosted automation scripts for media workflows, Unraid operations, and adjacent service helpers.

This repository groups small, focused utilities for self-hosted environments.
The current collection covers media workflow automation and Unraid-specific
operations, with each script documented in its own folder and maintained as a
standalone helper.

If this project saves you time or helps your setup, you can support ongoing
maintenance via Ko-fi or Buy Me a Coffee.

## Table of Contents

- [Background](#background)
- [Repository Layout](#repository-layout)
- [Available Scripts](#available-scripts)
- [Install](#install)
- [Usage](#usage)
- [Transparency](#transparency)
- [Maintainers](#maintainers)
- [Contributing](#contributing)
- [License](#license)

## Background

Self-hosted stacks often need small helper scripts for post-processing,
maintenance windows, queue handling, state transitions, and other operational
tasks that do not justify a full application. This repository collects those
utilities in one place and keeps each script documented next to its own source.

## Repository Layout

- `media/`: automation helpers for Radarr, SABnzbd, Tautulli, and adjacent
  media-service workflows
- `unraid/`: host-side helpers that are operationally tied to Unraid

Only active areas are documented here. New top-level sections should be added
when they contain published scripts, not as placeholders.

## Available Scripts

### Media

- [Auto Tag and Deferred Cleanup for Watched Movies](./media/radarr/auto_tag/)
- [Download Speed Monitor and Recovery Script](./media/sabnzbd/monitor_sab_speed/)
- [ISO Extractor Post-Processing Script](./media/sabnzbd/extract_iso/)
- [Delete Items From History Scripts](./media/sabnzbd/delete_item_from_history/)

See also the section index in [media/README.md](./media/README.md).

### Unraid

- [Appdata Backup Uptime Kuma Maintenance Helper](./unraid/appdata_backup_kuma_maintenance/)

See also the section index in [unraid/README.md](./unraid/README.md).

## Install

Clone the repository and then open the subdirectory for the script you want to
use.

```bash
git clone git@github.com:smoochy/homelab-automation-scripts.git
cd homelab-automation-scripts
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
and grouped under the relevant published area.

## License

[MIT](./LICENSE) 2026 [smoochy](https://github.com/smoochy)
