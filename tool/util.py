import os
from rich.console import Console
import pickle
import platform

CONF_FILE = "tool/data/.builder.pkl"
DEV_RELEASE = "https://github.com/devendrn/newb-shader/releases/download/dev/"
DEV_SHADERC_URL_PREFIX = DEV_RELEASE + "shaderc-"
SHADERC_PATH = os.path.join('tool', 'data', 'shaderc')
if os.name == 'nt':
    SHADERC_PATH += ".exe"


def print_styled_error(console: Console, log: str):
    log = log.strip().split('\n')
    for line in log:
        split_line = line.split()
        style = 'dim'
        if not split_line:
            continue
        if split_line[0] == "Command:":
            style = 'dim'
        elif split_line[0] == "Warning:":
            style = 'red'
        elif split_line[0] in ["Error:", ">>>", "cpp:"]:
            style = 'bold red'
        console.print(line, style=style)


def get_materials_path(mats: [str]):
    materials_path = os.path.join('src', 'materials')
    all_materials = os.listdir(materials_path)
    material_patterns = []
    for m in mats:
        if m not in all_materials:
            raise FileNotFoundError(m)
        material_patterns.append(os.path.join(materials_path, m))
    return material_patterns


def create_pack_manifest(config: dict) -> dict:
    return {
        'format_version': 2,
        'header': {
            "name": config['name'],
            "description": config['description'],
            "uuid": config['uuid'],
            "version": config['version'],
            "min_engine_version": config['min_supported_mc_version']
        },
        'modules': [
            {
                'type': 'resources',
                'uuid': '94a3e43c-276b-425a-b541-98465ebdb408',
                'version': config['version']
            }
        ],
        'subpacks': [],
        'metadata': {
            'authors': config['authors'],
            'contributors': config.get('contributors', []),
            'url': config['url']
        }
    }


def load_conf():
    try:
        with open(CONF_FILE, 'rb') as file:
            conf = pickle.load(file)
            if type(conf) is dict:
                return conf
        return {}
    except Exception:
        return {}


def save_conf(conf):
    with open(CONF_FILE, 'wb') as file:
        pickle.dump(conf, file)


def check_conf(console: Console):
    # returns None if setup needs update
    conf = load_conf()
    is_diff_machine = conf.get("os_name") != platform.system() or conf.get("arch") != platform.machine()
    is_diff_shaderc_url_prefix = conf.get("shaderc_url_prefix") != DEV_SHADERC_URL_PREFIX
    is_dependencies_present = os.path.exists(SHADERC_PATH)

    if is_diff_shaderc_url_prefix or is_diff_machine:
        console.print("Error: Incompatible or outdated shaderc binary.", style="red")
        conf = None
    if not is_dependencies_present:
        console.print("Error: 'setup' not done.", style="red")
        conf = None

    if conf is None:
        console.print("       Please run build setup again.", style="bold red")

    return conf
