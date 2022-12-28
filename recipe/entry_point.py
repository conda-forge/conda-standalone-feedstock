#!/spare/local/nwani/pyinstaller_stuff/dev/bin/python
# -*- coding: utf-8 -*-
import os
import sys

from concurrent.futures import Executor
from multiprocessing import freeze_support

# use this for debugging, because ProcessPoolExecutor isn't pdb/ipdb friendly
class DummyExecutor(Executor):
    def map(self, func, *iterables):
        for iterable in iterables:
            for thing in iterable:
                yield func(thing)

# This might be None!
CPU_COUNT = os.cpu_count()

# See validation results for magic number of 3
# https://dholth.github.io/conda-benchmarks/#extract.TimeExtract.time_extract?conda-package-handling=2.0.0a2&p-format='.conda'&p-format='.tar.bz2'&p-lang='py'&x-axis=format
DEFAULT_NUM_WORKERS = 1 if not CPU_COUNT else min(3, CPU_COUNT)



if __name__ == '__main__':
    freeze_support()
    # https://docs.python.org/3/library/multiprocessing.html#multiprocessing.freeze_support
    # Before any more imports, leave cwd out of sys.path for internal 'conda shell.*' commands.
    # see https://github.com/conda/conda/issues/6549
    if len(sys.argv) > 1 and sys.argv[1].startswith('shell.') and sys.path and sys.path[0] == '':
        # The standard first entry in sys.path is an empty string,
        # and os.path.abspath('') expands to os.getcwd().
        del sys.path[0]

    if len(sys.argv) > 1 and sys.argv[1].startswith('constructor'):
        import os
        import argparse
        from conda.base.constants import CONDA_PACKAGE_EXTENSIONS


        class NumProcessorsAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                """Converts a string representing the max number of workers to an integer
                while performing validation checks; raises argparse.ArgumentError if anything fails."""

                ERROR_MSG = "Max workers must be integer between 1 and the CPU count of the machine."

                try:
                    num = int(values)
                except ValueError as exc:
                    raise argparse.ArgumentError(self, ERROR_MSG) from exc

                if (num < 1):
                    raise argparse.ArgumentError(self, ERROR_MSG)

                # cpu_count can return None, so skip this check if that happens
                if CPU_COUNT:

                    # See Windows notes for magic number of 61
                    # https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor
                    max_cpu_num = min(CPU_COUNT, 61) if (os.name == "nt") else CPU_COUNT

                    if (num > max_cpu_num):
                        raise argparse.ArgumentError(self, ERROR_MSG)

                setattr(namespace, self.dest, num)


        p = argparse.ArgumentParser(description="constructor args")
        p.add_argument(
                '--prefix',
                action="store",
                required="True",
                help="path to conda prefix")
        p.add_argument(
                '--extract-conda-pkgs',
                action="store_true",
                help="extract all packages in $PREFIX/pkgs where $PREFIX is set by --prefix")
        p.add_argument(
                '--num-processors',
                action=NumProcessorsAction,
                default=DEFAULT_NUM_WORKERS,
                help="The number of processors to use for parallel package extraction")
        p.add_argument(
                '--extract-tarball',
                action="store_true",
                help="extract tarball from stdin")
        p.add_argument(
                '--make-menus',
                nargs='*',
                metavar='MENU_PKG',
                help="make menus")
        p.add_argument(
                '--rm-menus',
                action="store_true",
                help="rm menus")
        args, args_unknown = p.parse_known_args()
        args.prefix = os.path.abspath(args.prefix)
        os.chdir(args.prefix)
        if args.extract_conda_pkgs:
            import tqdm
            from conda_package_handling import api
            from concurrent.futures import ProcessPoolExecutor

            os.chdir("pkgs")
            flist = []
            for ext in CONDA_PACKAGE_EXTENSIONS:
                for pkg in os.listdir(os.getcwd()):
                    if pkg.endswith(ext):
                        fn = os.path.join(os.getcwd(), pkg)
                        flist.append(fn)
            with tqdm.tqdm(total=len(flist), leave=False) as t:
                with ProcessPoolExecutor(max_workers=args.num_processors) as executor:
                    for fn, _ in zip(flist, executor.map(api.extract, flist)):
                        t.set_description("Extracting : %s" % os.path.basename(fn))
                        t.update()

        if args.extract_tarball:
            import tarfile
            t = tarfile.open(mode="r|*", fileobj=sys.stdin.buffer)
            t.extractall()
            t.close()
        if (args.make_menus is not None) or args.rm_menus:
            import importlib.util
            utility_script = os.path.join(args.prefix, "Lib", "_nsis.py")
            spec = importlib.util.spec_from_file_location("constructor_utils", utility_script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if args.make_menus is not None:
                module.mk_menus(remove=False, prefix=args.prefix, pkg_names=args.make_menus, root_prefix=args.prefix)
            else:
                module.rm_menus(prefix=args.prefix, root_prefix=args.prefix)
        sys.exit()
    else:
        from conda.cli import main
        sys.exit(main())
