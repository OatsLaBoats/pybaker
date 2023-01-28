from src.pybaker.pybaker import *
import sys
import asyncio


def exe_c():
    builder = Builder("exe_c", "tests/exe_c/build", build_type = BuildType.DEBUG, cores = 4)

    if len(sys.argv) == 2 and sys.argv[1] == "clean":
        builder.clean_all()
        return

    lang = Languages.C()
      
    builder.add_language(lang)

    builder.add_path("tests/exe_c")

    builder.build()
    builder.link()
    

def dll_c():
    builder = Builder("dll_c", "tests/dll_c/build", build_type = BuildType.DEBUG)

    if len(sys.argv) == 2 and sys.argv[1] == "clean":
        builder.clean_all()
        return
  
    lang = Languages.C().set_compiler(Compiler_Clang())
    builder.add_language(lang)
    builder.set_linker(Linker_Static_Microsoft())

    builder.add_path("tests/dll_c")

    builder.build()
    builder.link()

if __name__ == "__main__":
    exe_c()