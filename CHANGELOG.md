# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release: `find_up` to locate a marker file or directory by walking up toward the
  filesystem root, and `walk_up` to iterate a directory and its ancestors.
- `find_up` accepts one name or several, takes an optional `root` stop boundary, and can
  restrict matches to files or directories through `kind`.
