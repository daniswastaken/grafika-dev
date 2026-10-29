import argparse
import pack
import build
import setup


PROFILE = 'multiplatform'


def main():
    parser = argparse.ArgumentParser(
        prog='build',
        description="Shader Builder: Wrapper for Lazurite, to build Grafika Shader for RenderDragon",
        epilog="GitHub: https://github.com/daniswastaken/grafika"
    )

    subparsers = parser.add_subparsers(help='sub-command', dest='subcommand')
    pack_parser = subparsers.add_parser('pack', help="build shader pack")
    pack_parser.set_defaults(func=pack.run, p=PROFILE)
    mats_parser = subparsers.add_parser('mats', help="build shader materials")
    mats_parser.set_defaults(func=build.run, p=PROFILE)
    setup_parser = subparsers.add_parser('setup', help="setup build tool")
    setup_parser.set_defaults(func=setup.run)

    mats_parser.add_argument(
        '-m',
        default=[],
        nargs='+',
        help="build materials (eg: Sky)"
    )

    mats_parser.add_argument(
        '-s',
        default="",
        help="subpack config to use (eg: NO_WAVE)"
    )

    for p in [pack_parser, mats_parser]:
        p.add_argument(
            '--lite',
            action='store_true',
            help='build with config_lite.h'
        )

    setup_parser.add_argument(
        '--reset',
        action='store_true',
        help="reset all data"
    )

    pack_parser.add_argument(
        '--no-zip',
        action='store_true',
        help="don't make archive"
    )

    pack_parser.add_argument(
        '--no-label',
        action='store_true',
        help="don't label materials"
    )

    pack_parser.add_argument(
        '-v',
        default="",
        help="version number eg: 46"
    )

    args = parser.parse_args()

    if args.subcommand is not None:
        args.func(args)
    else:
        parser.print_usage()
