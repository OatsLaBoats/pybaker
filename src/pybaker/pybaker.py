import os
import subprocess
import pickle
import platform
import datetime
import shutil
import concurrent.futures.thread as futh
import concurrent.futures as futures


OS = platform.system()

SLASH = "/"

EXECUTABLE_EXTENSION = ""
SHARED_LIB_EXTENSION = ""
STATIC_LIB_EXTENSION = ""

match OS:
    case "Windows":
        SLASH = "\\"
        EXECUTABLE_EXTENSION = ".exe"
        SHARED_LIB_EXTENSION = ".dll"
        STATIC_LIB_EXTENSION = ".lib"
    case "Linux":
        SHARED_LIB_EXTENSION = ".so"
        STATIC_LIB_EXTENSION = ".a"
    case "Darwin":
        SHARED_LIB_EXTENSION = ".dylib"
        STATIC_LIB_EXTENSION = ".a"


class BuildType:
    """
    The default optimization/debug levels of the build that are implemented by the preconfigured compilers and linkers.\n
    You can define your own if you implement your own compiler and linker configuration.
    """

    DEBUG = "debug"
    RELEASE_SMALL = "release_small"
    RELEASE_FAST = "release_fast"
    RELEASE_SAFE = "release_safe"


class DependencyScanner:
    """
    The base class of all dependency scanners. Inherit from this when writing your own scanner.
    """
    
    def __init__(self) -> None:
        pass


    def scan(self, file: str, line: str) -> str:
        """
        Scans a line of text for an import statement.
        """
        return None


class Compiler:
    """
    The base class of all compiler configurations. Inherit from this when writing your own compiler config.\n
    If you don't wish to write an entire compiler config, you can inherit from an existing one and modify the flags field
    in the constructor.
    """

    def __init__(self, flags: list[str] = None) -> None:
        self.object_extension = ".o"
        self.flags = flags

        if self.flags is None:
            self.flags: list[str] = []

    
    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        """
        Compiles a source file into an object file.\n
        build_type is a parameter that is normally provided by the 'BuildType' class. But if you wish any string can be passed.\n
        Returns False on success and True on failure.
        """
        print("[Error]: 'compile_file' is not implemented")
        return True
    

class Linker:
    """
    The linker base class. Use this to implement you own linker config.\n
    Its important to remember that unlike compilers only one linker can be used with each builder.\n
    If you don't wish to write an entire linker config, you can inherit from an existing one and modify the flags field
    in the constructor.
    """

    def __init__(self, flags: list[str] = None) -> None:
        self.flags = flags

        if self.flags is None:
            self.flags: list[str] = []


    # Returns True on failure
    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        """
        Links the object files into an executable or what ever else you defined.\n
        build_type is a parameter that is normally provided by the 'BuildType' class. But if you wish any string can be passed.\n
        Returns False on success and True on failure.
        """
        print("[Error]: 'link' is not implemented")
        return True


class Language:
    """
    Groups a scanner and a compiler to define a language.\n
    Use to define your own languages.
    """

    def __init__(self, file_extensions: set[str] = None, scanner: DependencyScanner = None, compiler: Compiler = None) -> None:
        self.file_extentions = file_extensions
        self.scanner = scanner
        self.compiler = compiler

        if self.file_extentions is None:
            self.file_extentions = set()
        if self.scanner is None:
            self.scanner = DependencyScanner()
        if self.compiler is None:
            self.compiler = Compiler_Invalid()


    def set_extension(self, file_exension: str):
        self.file_extentions = set([file_exension])
        return self
    
    
    def set_extensions(self, file_extensions: set[str]):
        self.file_extentions = file_extensions
        return self

    
    def add_extension(self, file_extension: str):
        self.file_extentions.add(file_extension)
        return self


    def add_extensions(self, file_extensions: set[str]):
        self.file_extentions |= file_extensions
        return self


    def set_scanner(self, scanner: DependencyScanner):
        self.scanner = scanner
        return self


    def set_compiler(self, compiler: Compiler):
        self.compiler = compiler
        return self


def _print_link_message(mode: str, output: str) -> None:
    match mode:
        case BuildType.DEBUG: print(f"[Info]: linking (debug) \"{output}\"")
        case BuildType.RELEASE_FAST: print(f"[Info]: linking (release fast) \"{output}\"")
        case BuildType.RELEASE_SAFE: print(f"[Info]: linking (release safe) \"{output}\"")
        case BuildType.RELEASE_SMALL: print(f"[Info]: linking (release small) \"{output}\"")


class Linker_Invalid(Linker):
    """An default invalid linker that will throw an error if used."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        print("[Error]: Could not find a linker automatically.")
        return True


class Linker_Executable_Clang(Linker):
    """Uses clang to call the system linker and link an executable."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{EXECUTABLE_EXTENSION}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        # There may be ways to make the execuatble smaller here but I'm not sure how.
        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["clang", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["clang", "-o", output] + params).returncode != 0


class Linker_Shared_Clang(Linker):
    """Uses clang to call the system linker and link a shared library."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{SHARED_LIB_EXTENSION}"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["clang", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["clang", "-o", output] + params).returncode != 0


class Linker_Executable_GCC(Linker):
    """Uses gcc to call ld linker and link an executable."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{EXECUTABLE_EXTENSION}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["gcc", "-g", "-o", output] + params).returncode != 0
            case _:
                return subprocess.run(["gcc", "-o", output] + params).returncode != 0
            

class Linker_Shared_GCC(Linker):
    """Uses gcc to call ld linker and link a shared library."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{SHARED_LIB_EXTENSION}"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["gcc", "-g", "-o", output] + params).returncode != 0
            case _:
                return subprocess.run(["gcc", "-o", output] + params).returncode != 0


class Linker_Executable_GNU(Linker):
    """Uses ld to link an executable."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{EXECUTABLE_EXTENSION}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        # There may be ways to make the execuatble smaller here but I'm not sure how.
        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["ld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld", "-o", output] + params).returncode != 0


class Linker_Shared_GNU(Linker):
    """Uses ld to link a shared library."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{SHARED_LIB_EXTENSION}"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        # There may be ways to make the execuatble smaller here but I'm not sure how.
        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["ld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld", "-o", output] + params).returncode != 0


class Linker_Static_GNU(Linker):
    """Uses ar to create a static library."""

    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{STATIC_LIB_EXTENSION}"
        params = self.flags + flags

        _print_link_message(build_type, output)

        return subprocess.run(["ar"] + params + ["-crs", output] + objects).returncode != 0


class Linker_Executable_LLVM(Linker):
    """Uses the llvm linker to link an executable for different platforms."""
    
    def __init__(self, flags: list[str] = None, operating_system: str = OS) -> None:
        super().__init__(flags)
        self.os = operating_system


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        match self.os:
            case "Windows": return self._lld_link(output_dir, output_name, build_type, objects, flags)
            case "Linux": return self._ld_lld(output_dir, output_name, build_type, objects, flags)
            case "Darwin": return self._ld64_lld(output_dir, output_name, build_type, objects, flags)
            case _: return super().link(output_dir, output_dir, build_type, objects, flags)
    

    def _ld_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{EXECUTABLE_EXTENSION}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["ld.lld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld.lld", "-o", output] + params).returncode != 0
    
    
    # Not implemented because I don't know how macos does things.
    def _ld64_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        print("[Error]: No implementation for darwin linker.")
        return True


    def _lld_link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{EXECUTABLE_EXTENSION}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["lld-link", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["lld-link", f"/OUT:{output}"] + params, shell=True).returncode != 0


class Linker_Shared_LLVM(Linker):
    """Uses the llvm linker to link a shared library for different platforms."""
    
    def __init__(self, flags: list[str] = None, operating_system: str = OS) -> None:
        super().__init__(flags)
        self.os = operating_system


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        match self.os:
            case "Windows": return self._lld_link(output_dir, output_dir, build_type, objects, flags)
            case "Linux": return self._ld_lld(output_dir, output_dir, build_type, objects, flags)
            case "Darwin": return self._ld64_lld(output_dir, output_dir, build_type, objects, flags)
            case _: return super().link(output_dir, output_dir, build_type, objects, flags)
    

    def _ld_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{SHARED_LIB_EXTENSION}"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                # This is the same as calling lld -flavor ld
                return subprocess.run(["ld.lld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld.lld", "-o", output] + params).returncode != 0
    
    
    def _ld64_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        print("[Error]: No implementation for darwin linker.")
        return True


    def _lld_link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{SHARED_LIB_EXTENSION}"
        common = ["/DLL"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["lld-link", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["lld-link", f"/OUT:{output}"] + params, shell=True).returncode != 0


class Linker_Static_LLVM(Linker):
    """Uses llvm-ar to create a static library."""

    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{STATIC_LIB_EXTENSION}"
        params = self.flags + flags

        _print_link_message(build_type, output)

        return subprocess.run(["llvm-ar"] + params + ["-crs", output] + objects).returncode != 0


class Linker_Executable_Microsoft(Linker):
    """Uses the microsoft linker to link an executable."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{EXECUTABLE_EXTENSION}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["link", "/NOLOGO", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["link", "/NOLOGO", f"/OUT:{output}"] + params, shell=True).returncode != 0


class Linker_Shared_Microsoft(Linker):
    """Uses the microsoft linker to link a shared library."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = SHARED_LIB_EXTENSION

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        common = ["/DLL"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["link", "/NOLOGO", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["link", "/NOLOGO", f"/OUT:{output}"] + params, shell=True).returncode != 0


class Linker_Static_Microsoft(Linker):
    """Uses lib.exe to create a static library."""

    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}{STATIC_LIB_EXTENSION}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        return subprocess.run(["lib", "/NOLOGO", f"/OUT:{output}"] + params, shell=True).returncode != 0


class Linker_Executable_TCC(Linker):
    """Uses tcc to link an executable."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = EXECUTABLE_EXTENSION

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["tcc", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["tcc", "-o", output] + params).returncode != 0


class Linker_Shared_TCC(Linker):
    """Uses tcc to link an executable."""
    
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = SHARED_LIB_EXTENSION

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["tcc", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["tcc", "-o", output] + params).returncode != 0


class DependencyScanner_C(DependencyScanner):
    """
    The default C dependency scanner. This is an example on how to implement one.
    Its not perfect so if you have problems feel free to create your own.
    """
    
    def __init__(self) -> None:
        super().__init__()
    

    def scan(self, file: str, line: str) -> str:
        # We will ignore #include <> since it is usually used to include libraries that don't get modified.

        tokens = line.split()

        if len(tokens) < 2:
            return None

        if tokens[0] != "#include" and not tokens[1].startswith("\""):
            return None

        # Get the path of the source file.
        path = file[:file.rfind(SLASH)]
        dep = tokens[1].strip("\"")

        # Construct the full path of the dependency.
        fullpath = os.path.abspath(f"{path}{SLASH}{dep}")
        return fullpath
    

class DependencyScanner_CPP(DependencyScanner):
    """
    The default CPP dependency scanner. This is an example on how to implement one.
    Its not perfect so if you have problems feel free to create your own.
    """
    def __init__(self) -> None:
        super().__init__()
    

    def scan(self, file: str, line: str) -> str:
        tokens = line.split()

        if len(tokens) < 2:
            return None

        if tokens[0] != "#include" and not tokens[1].startswith("\""):
            return None

        path = file[:file.rfind(SLASH)]
        dep = tokens[1].strip("\"")
        fullpath = os.path.abspath(f"{path}{SLASH}{dep}")
        return fullpath


def _print_compile_message(mode: str, source: str, precent: float = None) -> None:
    if precent is None:
        match mode:
            case BuildType.DEBUG: print(f"[Info]: building (debug) \"{source}\"")
            case BuildType.RELEASE_FAST: print(f"[Info]: building (release fast) \"{source}\"")
            case BuildType.RELEASE_SAFE: print(f"[Info]: building (release safe) \"{source}\"")
            case BuildType.RELEASE_SMALL: print(f"[Info]: building (release small) \"{source}\"")
    else:
        prec = int(precent * 100)
        s = str(prec).rjust(2, " ")
        match mode:
            case BuildType.DEBUG: print(f"[Info]: {s}% building (debug) \"{source}\"")
            case BuildType.RELEASE_FAST: print(f"[Info]: {s}% building (release fast) \"{source}\"")
            case BuildType.RELEASE_SAFE: print(f"[Info]: {s}% building (release safe) \"{source}\"")
            case BuildType.RELEASE_SMALL: print(f"[Info]: {s}% building (release small) \"{source}\"")


class Compiler_Invalid(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        print("[Error]: Could not find a compiler automatically.")
        return False


class Compiler_Clang(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file, prec)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["clang", "-O0", "-g", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["clang", "-O3", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["clang", "-O3", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["clang", "-Os", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0

        return True


class Compiler_Clangpp(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file, prec)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["clang++", "-O0", "-g", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["clang++", "-O3", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["clang++", "-O3", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["clang++", "-Os" "-DNDEBUG", "-o", output, source_file] + params).returncode != 0

        return True


class Compiler_GCC(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file, prec)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["gcc", "-O0", "-g", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["gcc", "-O3", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["gcc", "-O3", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["gcc", "-Os", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0

        return True


class Compiler_GPP(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file, prec)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["g++", "-O0", "-g", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["g++", "-O3", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["g++", "-O3", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["g++", "-Os", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0

        return True


class Compiler_Microsoft_C(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
        self.object_extension = ".obj"

    
    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["/c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file, prec)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["cl", "/nologo", "/Od", "/Zi", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["cl", "/nologo", "/O2", "/DNDEBUG", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["cl", "/nologo", "/O2", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["cl", "/nologo", "/O1", "/DNDEBUG", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0

        return True


class Compiler_Microsoft_CPP(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
        self.object_extension = ".obj"

   
    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["/c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file, prec)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["cl", "/nologo", "/Od", "/Zi", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["cl", "/nologo", "/O2", "/DNDEBUG", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["cl", "/nologo", "/O2", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["cl", "/nologo", "/O1", "/DNDEBUG", f"/Fd{output_dir}{SLASH}", f"/Fo{output}", source_file] + params, shell=True).returncode != 0

        return True


class Compiler_TCC(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str], prec: float) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file, prec)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["tcc", "-g", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["tcc", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["tcc", "-o", output, source_file] + params).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["tcc", "-DNDEBUG", "-o", output, source_file] + params).returncode != 0

        return True


# Automatic tool detection
DEFAULT_C_COMPILER: Compiler = Compiler_Invalid()
DEFAULT_CPP_COMPILER: Compiler = Compiler_Invalid()
DEFAULT_LINKER: Linker = Linker_Invalid()

match OS:
    case "Windows": 
        if shutil.which("clang") is not None:
            DEFAULT_C_COMPILER = Compiler_Clang(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_CPP_COMPILER = Compiler_Clangpp(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = Linker_Executable_Clang()
        elif shutil.which("cl") is not None:
            DEFAULT_C_COMPILER = Compiler_Microsoft_C(["/Wall"])
            DEFAULT_CPP_COMPILER = Compiler_Microsoft_CPP(["/Wall"])
            DEFAULT_LINKER = Linker_Executable_Microsoft()
        elif shutil.which("gcc") is not None:
            DEFAULT_C_COMPILER = Compiler_GCC(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_CPP_COMPILER = Compiler_GPP(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = Linker_Executable_GCC()
    
    case "Linux":
        if shutil.which("clang") is not None:
            DEFAULT_C_COMPILER = Compiler_Clang(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_CPP_COMPILER = Compiler_Clangpp(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = Linker_Executable_Clang()
        elif shutil.which("gcc") is not None:
            DEFAULT_C_COMPILER = Compiler_GCC(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_CPP_COMPILER = Compiler_GPP(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = Linker_Executable_GCC()

    case "Darwin":
        if shutil.which("clang") is not None:
            DEFAULT_C_COMPILER = Compiler_Clang(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_CPP_COMPILER = Compiler_Clangpp(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = Linker_Executable_Clang()
        

class Languages:
    """
    Preconfigured languages.
    """

    def C() -> Language: 
        return Language({".c"}, DependencyScanner_C(), DEFAULT_C_COMPILER)
    
    
    def CPP() -> Language: 
        return Language({".cpp", ".cc", ".cxx"}, DependencyScanner_CPP(), DEFAULT_CPP_COMPILER)


class SourcePath:
    """
    Represents a group of source files. \n
    If the flags field is used then it is assumed that the source files are of the same language. \n
    Don't add an extra slash at the end of path.
    """
    
    def __init__(self, path: str = ".", files: list[str] = None, flags: list[str] = None) -> None:
        self.path = path
        self.files = files
        self.flags = flags

        if self.files is None:
            self.files = []

        if self.flags is None:
            self.flags = []

            
class _SourceFile:
    def __init__(self, path: str, flags: list[str], lang: Language):
        self.path = path
        self.flags = flags
        self.lang = lang


class Builder:
    """
    The core of your build file. You can create multiple ones for different targets. Just make sure that a different build directory is provided.\n
    call 'build()' to build your project.\n
    call 'link(flags)' to link it. \n
    call 'add_language(language)' to add support for a language. \n
    call 'add_source_path(source_path_object)' to add a group of source files.\n
    call 'add_path(path_str)' to automatically scan a directory for source files of the supported languages and add them all to a source path.\n
    call 'add_source(path_str)' adds one singular file to its own unique source path with its own unique flags.\n
    call 'clean_database' if you want to reset the build database without deleting the whole build directory. \n
    call 'clean_all' to delete the whole build directory.
    """

    def __init__(
        self, 
        project_name: str, 
        build_path: str = f".{SLASH}build", 
        build_type: str = BuildType.RELEASE_FAST, 
        linker: Linker = DEFAULT_LINKER,
        cores: int = 1
    ) -> None:
        """If using multiple builders you should specify a different build path for each one."""

        self._project_name = project_name
        self._languages: list[Language] = []
        self._source_paths: list[SourcePath] = []
        self._build_type = build_type
        self._linker = linker
        self._build_path = os.path.abspath(build_path)
        self._output_path = f"{self._build_path}{SLASH}{build_type}"
        self._pybaker_path = f"{self._build_path}{SLASH}.pybaker"
        self._object_path = f"{self._pybaker_path}{SLASH}objects_{build_type}"
        self._database = _BuildDatabase(f"{self._pybaker_path}{SLASH}build_database.pickle")
        self._should_link = False
        self._error = False
        self._cores = cores

        os.makedirs(self._output_path, exist_ok=True)
        os.makedirs(self._object_path, exist_ok=True)


    def add_language(self, language: Language) -> None:
        self._languages.append(language)


    def set_linker(self, linker: Linker) -> None:
        self._linker = linker
    

    def add_source_path(self, path: SourcePath) -> None:
        self._source_paths.append(path)


    def add_path(self, path: str, flags: list[str] = None) -> None:
        """
        Autodetects source files of supported languages. The flags parameter should only be used
        if you are certain that the directory contains only files of one language. The path should not end with a slash.
        """

        sp = SourcePath(path=path, flags=flags)

        # This looks very disgusting, but I don't know regex and I don't plan learning to make this cleaner.
        for f in os.listdir(path):
            if os.path.isfile(f"{path}{SLASH}{f}"):
                for lang in self._languages:
                    for ext in lang.file_extentions:
                        if f.endswith(ext):
                            sp.files.append(f)

        self.add_source_path(sp)


    def add_source(self, file: str, flags: list[str] = None) -> None:
        self.add_source_path(SourcePath(files=[file], flags=flags))


    def add_paths(self, paths: list[str], flags: list[str] = None) -> None:
        for path in paths:
            self.add_path(path, flags)
        
    
    def add_sources(self, files: list[str], flags: list[str] = None) -> None:
        self.add_source_path(SourcePath(files=files, flags=flags))
    

    def build(self, flags: list[str] = None) -> bool:
        """Builds the project. If the build fails it returns True."""
        if flags is None:
            flags = []
        
        self._database.load()

        files_to_build = self._check(flags)
        self._build(files_to_build)

        self._database.save()

        if self._error:
            print("[Error]: Build failed")
            return True

        return False


    def link(self, flags: list[str] = None) -> bool:
        """Links the project. Returns True on failure."""
        if flags is None:
            flags = []

        if self._error:
            return False

        if not self._should_link and not self._database.get_link_error():
            return False
        
        if self._linker is None:
            print(f"[Error]: No linker available")
            return True
        
        objects: list[str] = []
        objs = self._database.get_objects(self._build_type)
        for obj in objs:
            objects.append(f"{self._object_path}{SLASH}{obj}")
        
        if self._linker.link(self._output_path, self._project_name, self._build_type, objects, flags):
            print("[Error]: Linking failed")
            self._database.set_link_error(True)
            self._database.save()
            return True
        
        self._database.set_link_error(False)
        self._database.save()
        
        return False


    def clean_database(self) -> None:
        os.remove(self._database._path)


    def clean_all(self) -> None:
        shutil.rmtree(self._build_path)


    def run_output(self, params: list[str] = None) -> int:
        if params is None:
            params = []
        
        return subprocess.run([f"{self._output_path}{SLASH}{self._project_name}{EXECUTABLE_EXTENSION}"] + params).returncode
    
    
    def _check(self, flags: list[str]) -> list[_SourceFile]:
        result: list[_SourceFile] = []
        
        for path in self._source_paths:
            path.flags += flags
            result += self._check_source_path(path)

        return result
    
    
    def _check_source_path(self, path: SourcePath) -> list[_SourceFile]:
        result: list[_SourceFile] = []

        for file in path.files:
            full_file_path = os.path.abspath(f"{path.path}{SLASH}{file}")
            sf = self._check_file(full_file_path, path.flags)
            
            if sf is not None:
                result.append(sf)
        
        return result
        

    def _check_file(self, file: str, flags: list[str]) -> _SourceFile:
        source_filename = file[file.rfind(SLASH) + 1:file.rfind(".")]
        source_filepath = file[:file.rfind(SLASH)]

        ext = file[file.rfind("."):]
        flag_str = " ".join(flags)

        language = self._get_language(ext)
        if language is None:
            print(f"[Error]: Source file \"{file}\" is written in an unsupported language")
            self._error = True
            return

        if self._error:
            return

        obj_prefix = source_filepath.replace(SLASH, "_").replace(":", "_") + "_"
        obj_filename = f"{obj_prefix}{source_filename}{language.compiler.object_extension}"
        should_rebuild = False
        
        if not os.path.exists(f"{self._object_path}{SLASH}{obj_filename}"):
            should_rebuild = True
        else:
            data = self._database.query_source(file)
            time_stamp = os.stat(file).st_mtime

            if data is None:
                should_rebuild = True
            elif time_stamp > data.last_write_time:
                should_rebuild = True
            elif data.flags != flag_str:
                should_rebuild = True
            else:
                for dep in data.dependencies:
                    dep_time_stamp = os.stat(dep).st_mtime
                    if dep_time_stamp > data.last_write_time:
                        now = datetime.datetime.now().timestamp()
                        os.utime(file, (now, now))
                        should_rebuild = True
                        break

        if should_rebuild:
            return _SourceFile(file, flags, language)
        
        return None


    def _build(self, files_to_build: list[_SourceFile]) -> None:
        if self._error:
            return

        if self._cores <= 0:
            print("[Error]: Can't build with 0 or less cores")
            self._error = True
            return

        with futh.ThreadPoolExecutor(max_workers = self._cores) as e:
            total_files = len(files_to_build)
            file_count = 0

            chunk: list[_SourceFile] = []

            for file in files_to_build:
                chunk.append(file)

                if len(chunk) == self._cores:
                    fs: list[futures.Future] = []

                    for i in chunk:
                        prec = float(file_count) / float(total_files)
                        fs.append(e.submit(self._build_file, i, prec))
                        file_count += 1

                    for future in fs:
                        future.result()

                    chunk.clear()
            
            if len(chunk) > 0:
                fs: list[futures.Future] = []

                for i in chunk:
                    prec = float(file_count) / float(total_files)
                    fs.append(e.submit(self._build_file, i, prec))
                    file_count += 1

                for future in fs:
                    future.result()


    def _build_file(self, source_file: _SourceFile, prec: float) -> None:
        if self._error:
            return

        file = source_file.path
        flags = source_file.flags
        language = source_file.lang

        source_filename = file[file.rfind(SLASH) + 1:file.rfind(".")]
        source_filepath = file[:file.rfind(SLASH)]

        flag_str = " ".join(flags)

        obj_prefix = source_filepath.replace(SLASH, "_").replace(":", "_") + "_"
        obj_filename = f"{obj_prefix}{source_filename}{language.compiler.object_extension}"

        if language.compiler.compile_file(self._object_path, obj_filename, file, self._build_type, flags, prec):
                self._error = True
                return

        self._should_link = True
        deps = self._get_deps(file, language)
        write_time = os.stat(file).st_mtime
        source_data = _SourceData(deps, write_time, flag_str)
        self._database.update_source(file, source_data)
        self._database.add_object(obj_filename, self._build_type)


    def _get_language(self, ext: str) -> Language:
        for language in self._languages:
            if ext in language.file_extentions:
                return language
        return None

    
    def _get_deps(self, file: str, lang: Language, result: set[str] = None) -> set[str]:
        if result is None:
            result = set()

        with open(file, "r") as f:
            lines = f.readlines()
            for line in lines:
                dep = lang.scanner.scan(file, line)
                if dep is None or dep in result or not os.path.exists(dep):
                    continue

                result.add(dep)
                self._get_deps(dep, lang, result)
        
        return result
    

class _SourceData:
    def __init__(self, dependencies: set[str] = [], last_write_time: float = 0.0, flags: str = "") -> None:
        self.dependencies = dependencies
        self.last_write_time = last_write_time
        self.flags = flags


class _DatabaseFileContents:
    def __init__(self) -> None:
        self.link_error = False
        
        # key = filename, value = file data
        self.sources: dict[str, _SourceData] = {}

        # objects should be different for earch build type
        self.objects: dict[str, set[str]] = {}


class _BuildDatabase:
    def __init__(self, database_path: str) -> None:
        self._path = database_path
        self._data = _DatabaseFileContents()


    def load(self) -> None:
        if not os.path.exists(self._path):
            return

        with open(self._path, "rb") as f:
            self._data = pickle.load(f)


    def save(self) -> None:
        with open(self._path, "wb") as f:
            pickle.dump(self._data, f, pickle.HIGHEST_PROTOCOL)


    def query_source(self, filename: str) -> _SourceData:
        if filename in self._data.sources:
            return self._data.sources[filename]
        return None
    

    def update_source(self, filename: str, data: _SourceData) -> None:
        self._data.sources[filename] = data


    def add_object(self, filename: str, build_type: str) -> None:
        if build_type not in self._data.objects:
            self._data.objects[build_type] = set()
        self._data.objects[build_type].add(filename)
    

    def remove_object(self, filename: str, build_type: str) -> None:
        self._data.objects[build_type].remove(filename)


    def clear_objects(self, build_type: str) -> None:
        self._data.objects[build_type].clear()
    

    def get_objects(self, build_type: str) -> set[str]:
        return self._data.objects[build_type]

    
    def set_link_error(self, status: bool) -> None:
        self._data.link_error = status


    def get_link_error(self) -> None:
        return self._data.link_error