import os
from distutils.core import setup

from Cython.Build import cythonize


def main():
    os.rename('main.py', 'RADeline.py')
    setup(name='RADeline', ext_modules=cythonize('RADeline.py', nthreads=2, annotate=True, compiler_directives={'warn.unused': True, 'warn.unused_arg': True, 'warn.unused_result': True}))
    os.rename('RADeline.py', 'main.py')

    os.chdir('movement sim')
    os.rename('sim.py', 'sim_compiled.py')
    setup(name='sim_compiled', ext_modules=cythonize('sim_compiled.py', nthreads=2, annotate=True, compiler_directives={'warn.unused': True, 'warn.unused_arg': True, 'warn.unused_result': True}))
    os.rename('sim_compiled.py', 'sim.py')


if __name__ == '__main__':
    main()
