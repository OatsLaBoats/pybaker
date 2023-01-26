
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
    builder = Builder("test", build_type=BuildType.DEBUG, cores = 4)

    # To see how to implement a language configuration check out 
    # the Languages class.
    builder.add_language(Languages.C())

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

</br>

## 2.0.0 Release Notes:

---

1. Many classes and functions have been renamed for clarity.
2. The language presets are now functions tha treturn a language rather than static members so they can be safely modified.
3. The dependency scanner API has been simplified.
4. Added gcc as a linker option similar to clang.
5. Added a way to extend existing language configurations without needing to create a new one.
6. The precentage of compilation done is now printed to the teminal along with the building file message. This requires passing an extra paramete to the compile function.
7. Now allows for multithreaded building. You can select the number of cores by setting the cores parameter in the Builder constructor.
8. Added a tcc configuration.
9. Added static library linker options.
