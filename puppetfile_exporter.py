import re
import argparse
import requests
import git
import gitlab
import tempfile
import shutil
from urllib.parse import urlparse
from prometheus_client import start_http_server, Gauge
import time

module_version_gauge = Gauge(
    'puppet_module_version',
    'Compare version current and latest versions of Puppet module',
    ['module', 'current_version', 'latest_version']
)

def parse_puppetfile(puppetfile_path):
    modules = {}
    with open(puppetfile_path, 'r') as file:
        lines = file.readlines()
        for i, line in enumerate(lines):
            match = re.match(r"mod '([^']+)',\s*'([^']+)'", line)
            if match:
                module_name = match.group(1)
                module_version = match.group(2)
                modules[module_name] = {'version': module_version, 'type': 'forge'}
            else:
                match_git = re.match(r"mod '([^']+)',", line)
                if match_git:
                    module_name = match_git.group(1)
                    git_repo = None
                    tag_version = None
                    for j in range(i+1, len(lines)):
                        next_line = lines[j]
                        git_match = re.search(r":git\s*=>\s*'([^']+)'", next_line)
                        tag_match = re.search(r":tag\s*=>\s*'([^']+)'", next_line)
                        if git_match:
                            git_repo = git_match.group(1)
                        if tag_match:
                            tag_version = tag_match.group(1)
                        if git_repo and tag_version:
                            modules[module_name] = {'version': tag_version, 'type': 'git', 'repo': git_repo}
                            break
                        if re.match(r"\s*mod\s", next_line):
                            break
    return modules

def get_latest_forge_version(module_name):
    url = f"https://forgeapi.puppet.com/v3/modules/{module_name}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['current_release']['version']
    return None

def get_latest_git_tag(repo_url, gitlab_token=None, gitlab_host=None):
    parsed_url = urlparse(repo_url)
    hostname = parsed_url.hostname

    if gitlab_host and gitlab_host in hostname:
        return get_latest_gitlab_tag(repo_url, gitlab_token, gitlab_host)
    else:
        return get_latest_generic_git_tag(repo_url)

def get_latest_gitlab_tag(repo_url, gitlab_token, gitlab_host):
    repo_info = repo_url.replace(f"ssh://git@{gitlab_host}", "").replace(".git", "").replace(":", "/")
    gl = gitlab.Gitlab(f'https://{gitlab_host}', gitlab_token)
    try:
        project = gl.projects.get(repo_info)
        tags = project.tags.list(iterator=True)
        return next(tags, None).name if tags else None
    except gitlab.GitlabHttpError:
        return None

def get_latest_generic_git_tag(repo_url):
    temp_dir = tempfile.mkdtemp()
    try:
        repo = git.Repo.clone_from(repo_url, temp_dir, depth=1)
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
        return tags[-1].name if tags else None
    finally:
        shutil.rmtree(temp_dir)

def update_metrics(modules, gitlab_token, gitlab_host):
    existing_metrics = set(module_version_gauge._metrics.keys())
    for module, info in modules.items():
        current_version = info.get('version', '0')

        if info['type'] == 'forge':
            latest_version = get_latest_forge_version(module)
        elif info['type'] == 'git':
            latest_version = get_latest_git_tag(info['repo'], gitlab_token, gitlab_host)
        else:
            latest_version = None

        found_metric = next((metric for metric in existing_metrics if metric[0] == module), None)
        if found_metric:
            module_version_gauge.remove(*found_metric)
        module_version_gauge.labels(
            module=module,
            current_version=current_version,
            latest_version=latest_version or 'unknown'
        ).set(0 if current_version == latest_version else 1)

def main():
    parser = argparse.ArgumentParser(description='Check latest versions of Puppet modules')
    parser.add_argument('--puppetfile', type=str, default='/etc/puppetlabs/code/environments/production/Puppetfile',
                        help='Path to Puppetfile')
    parser.add_argument('--gitlab-token', type=str, help='Private token for GitLab API')
    parser.add_argument('--gitlab-host', type=str, help='GitLab hostname for private repos (e.g., git.example.com)')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the exporter on')
    parser.add_argument('--interval', type=int, default=60, help='Interval to update metrics (in seconds)')
    args = parser.parse_args()

    start_http_server(args.port)
    print(f"Starting Prometheus exporter on port {args.port}")

    while True:
        modules = parse_puppetfile(args.puppetfile)
        update_metrics(modules, args.gitlab_token, args.gitlab_host)
        time.sleep(args.interval)

if __name__ == '__main__':
    main()
