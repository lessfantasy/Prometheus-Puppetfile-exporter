# Puppet Module Version Exporter

This tool parses a [Puppetfile](https://puppet.com/docs/code/puppetfile.html), detects the current versions of Puppet modules (from Forge or Git), compares them to the latest available versions, and exposes this information as Prometheus metrics.

## Supported Module Sources

- **Forge modules** (e.g. `mod 'puppetlabs/stdlib', '8.7.0'`)
- **Git modules** (with tags):
  - GitLab (via API)
  - GitHub (via `git clone`)
  - Other generic Git repositories

## Example Puppetfile

```ruby
# Forge module
mod 'puppetlabs/stdlib', '8.7.0'

# GitHub module
mod 'myorg/custom_module',
  :git => 'https://github.com/myorg/custom_module.git',
  :tag => 'v1.2.3'

# GitLab module
mod 'internal/secure_module',
  :git => 'ssh://git@git.example.com/group/secure_module.git',
  :tag => 'v0.9.1'

```

## Installation

### From GitHub Actions

Open a successful **Build exporter** run and download `exporter-debian-amd64-<attempt>` from **Artifacts**. It contains a standalone executable in a `.tar.gz` and a Debian `.deb`. Both are built for Linux `amd64` on Debian 12 and bundle Python. The standalone executable requires `git` on the host.

From the extracted artifact directory, install the Debian package or unpack and run the standalone executable.

```sh
sudo apt install ./prometheus-puppetfile-exporter_*.deb
prometheus-puppetfile-exporter --help
```

```sh
tar -xzf prometheus-puppetfile-exporter-linux-amd64.tar.gz
./prometheus-puppetfile-exporter --help
```

### From source

1. Clone the repository

git clone https://github.com/yourname/puppet-module-version-exporter.git
cd puppet-module-version-exporter

2. Install dependencies

pip install -r requirements.txt

Requirements: Python ≥ 3.7, git command-line tool, access to the Puppetfile and the corresponding repositories.

## Usage

python puppetfile_exporter.py \
  --puppetfile /path/to/Puppetfile \
  --port 8000 \
  --interval 300 \
  --gitlab-host git.example.com \
  --gitlab-token $GITLAB_TOKEN

For an installed package, replace `python puppetfile_exporter.py` with `prometheus-puppetfile-exporter`.

Command-line options

Option	Description
--puppetfile	Path to the Puppetfile (default: /etc/puppetlabs/code/...)
--port	Port to expose Prometheus metrics on (default: 8000)
--interval	Metrics update interval in seconds (default: 60)
--gitlab-host	(Optional) GitLab host for API access
--gitlab-token	(Optional) GitLab private token for API access

## Prometheus Metrics

The exporter exposes the following metric at the specified port:

puppet_module_version{module="puppetlabs/stdlib", current_version="8.7.0", latest_version="9.0.0"} 1

    A value of 1 indicates that a newer version is available.

    A value of 0 means the current version is up-to-date.

## GitLab API Access

If some modules are hosted in a private GitLab instance, provide the host and an access token via --gitlab-host and --gitlab-token. GitHub and other repositories will be accessed via shallow git clone operations and do not require API tokens.
