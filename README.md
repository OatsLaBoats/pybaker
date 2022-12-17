
# 🥧pybaker🥧

Pybaker is an easy to use flexible build system, provided as a python library. Born from my frustrations with existing build systems.

The library provides a Builder object and also allows you to create your own compiler, linker, dependency scanner and language configuration.
It comes with a few Premade configurations but I would recomend using the clang configuration.

Install it from pip.

Example build script:

``` Python
# If clang is installed this will just work.

from pybaker import *


def build():
    builder = Builder("test", build_type=BuildType.DEBUG)

    # To see how to implement a language configuration check out 
    # the Languages class.
    builder.add_language(Languages.C)

    builder.add_path("src")

    if builder.build():
        # Do something on failure...
        pass

    if builder.link(["-lUser32.lib", "-lGdi32.lib"]):
        # Do something on failure...
        pass


if __name__ == "__main__":
    build()
```

To run it you simply call from your base directory  

``` shell
python build.py 
```

This will create a new directory where it will dump its private files. A well as the build results.  
