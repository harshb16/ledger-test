"""Fetch immutable upstream artifacts and verify their pinned hashes."""
from pathlib import Path
import hashlib
import urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[1]

def main():
    config = yaml.safe_load((ROOT / 'configs/phase1_prereg.yaml').read_text())['data']
    manifest = yaml.safe_load((ROOT / 'configs/data_manifest.yaml').read_text())
    for name in config['files']:
        path = ROOT / 'data/raw' / Path(name).name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            host = 'media.githubusercontent.com/media' if 'public_individual' in name else 'raw.githubusercontent.com'
            data = urllib.request.urlopen(f'https://{host}/forecastingresearch/forecastbench-datasets/{config["commit"]}/{name}').read()
            if hashlib.sha256(data).hexdigest() != manifest[path.name]:
                raise ValueError(f'Checksum mismatch: {name}')
            path.write_bytes(data)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[path.name], path
        print(f'Verified {path.name}')

if __name__ == '__main__':
    main()
