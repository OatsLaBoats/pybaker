import os
import subprocess
import pickle
import platform
import datetime
import shutil

# Constants
SLASH = "/"
DYNAMIC_LIB_EXTENSION = ""
EXECUTABLE_EXTENSION = ""
match platform.system():
    case "Windows": 
        SLASH = "\\"
        DYNAMIC_LIB_EXTENSION = ".dll"
        EXECUTABLE_EXTENSION = ".exe"
    case "Linux":   
        DYNAMIC_LIB_EXTENSION = ".so"
    case "Darwin":  
        DYNAMIC_LIB_EXTENSION = ".dylib"


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


    def get_dependencies(self, file: str) -> set[str]:
        """
        Returns a list of the absolute file paths of the dependencies.
        """
        return []


class Compiler:
    """
    The base class of all compiler configurations. Inherit from this when writing your own compiler config.\n
    If you don't wish to write an entire compiler config, you can inherit from an existing one and modify the flags field
    in the constructor.
    """

    def __init__(self, flags: list[str] = None) -> None:
        self.flags = flags
        if self.flags == None:
            self.flags = []

    
    def get_object_file_extension(self) -> str:
        """
        Returns the prefered file extension for objects. For example .o or .obj
        """
        return ".o"


    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
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
        if self.flags == None:
            self.flags = []


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
    
    def __init__(self, file_extensions: set[str], scanner: DependencyScanner, compiler: Compiler) -> None:
        self.file_extentions = file_extensions
        self.scanner = scanner
        self.compiler = compiler


def _print_link_message(mode: str, output: str) -> None:
    match mode:
        case BuildType.DEBUG: print(f"[Info]: linking (debug) \"{output}\"")
        case BuildType.RELEASE_FAST: print(f"[Info]: linking (release fast) \"{output}\"")
        case BuildType.RELEASE_SAFE: print(f"[Info]: linking (release safe) \"{output}\"")
        case BuildType.RELEASE_SMALL: print(f"[Info]: linking (release small) \"{output}\"")


class LinkerInvalid(Linker):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        print("[Error]: Could not find a linker automatically.")
        return True


# Closest thing to a cross platform linker
class LinkerClangExe(Linker):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = EXECUTABLE_EXTENSION

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        # There may be ways to make the execuatble smaller here but I'm not sure how.
        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["clang", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["clang", "-o", output] + params).returncode != 0


# Not sure if -fpic flag should be included. If you need it pass as a parameter.
class LinkerClangDynamicLib(Linker):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = DYNAMIC_LIB_EXTENSION
        
        output = f"{output_dir}{SLASH}{output_name}{ext}"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["clang", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["clang", "-o", output] + params).returncode != 0


class LinkerGnuExe(Linker):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = EXECUTABLE_EXTENSION

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        # There may be ways to make the execuatble smaller here but I'm not sure how.
        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["ld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld", "-o", output] + params).returncode != 0


class LinkerGnuDynamicLib(Linker):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = DYNAMIC_LIB_EXTENSION

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        # There may be ways to make the execuatble smaller here but I'm not sure how.
        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["ld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld", "-o", output] + params).returncode != 0


# This is the preconfigured cross linker
class LinkerLLDExe(Linker):
    def __init__(self, flags: list[str] = None, operating_system: str = platform.system()) -> None:
        super().__init__(flags)
        self.platform = operating_system


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        match self.platform:
            case "Windows": return self._lld_link(output_dir, output_dir, build_type, objects, flags)
            case "Linux": return self._ld_lld(output_dir, output_dir, build_type, objects, flags)
            case "Darwin": return self._ld64_lld(output_dir, output_dir, build_type, objects, flags)
            case _: return super().link(output_dir, output_dir, build_type, objects, flags)
    

    def _ld_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["ld.lld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld.lld", "-o", output] + params).returncode != 0
    
    
    # Not implemented because I don't know how macos does things
    def _ld64_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        print("[Error]: No implementation for darwin linker.")
        return True


    def _lld_link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}.exe"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["lld-link", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["lld-link", f"/OUT:{output}"] + params, shell=True).returncode != 0


class LinkerLLDDynamicLib(Linker):
    def __init__(self, flags: list[str] = None, operating_system: str = platform.system()) -> None:
        super().__init__(flags)
        self.platform = operating_system


    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        match self.platform:
            case "Windows": return self._lld_link(output_dir, output_dir, build_type, objects, flags)
            case "Linux": return self._ld_lld(output_dir, output_dir, build_type, objects, flags)
            case "Darwin": return self._ld64_lld(output_dir, output_dir, build_type, objects, flags)
            case _: return super().link(output_dir, output_dir, build_type, objects, flags)
    

    def _ld_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}.so"
        common = ["-shared"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["ld.lld", "-g", "-o", output] + params).returncode != 0
            case _: 
                return subprocess.run(["ld.lld", "-o", output] + params).returncode != 0
    
    
    def _ld64_lld(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        print("[Error]: No implementation for darwin linker.")
        return True


    def _lld_link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}.dll"
        common = ["/DLL"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["lld-link", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["lld-link", f"/OUT:{output}"] + params, shell=True).returncode != 0


# For some reason it likes generating a pdb file in the base directory and there doesn't seem to be a way to stop it.
class LinkerMicrosoftExe(Linker):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = ".exe"

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        params = self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["link", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["link", f"/OUT:{output}"] + params, shell=True).returncode != 0


class LinkerMicrosoftDynamicLib(Linker):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def link(self, output_dir: str, output_name: str, build_type: str, objects: list[str], flags: list[str]) -> bool:
        ext = ".dll"

        output = f"{output_dir}{SLASH}{output_name}{ext}"
        common = ["/DLL"]
        params = common + self.flags + flags + objects

        _print_link_message(build_type, output)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["link", "/DEBUG", f"/OUT:{output}", f"/PDB:{output_dir}{SLASH}{output_name}.pdb"] + params, shell=True).returncode != 0
            case _:
                return subprocess.run(["link", f"/OUT:{output}"] + params, shell=True).returncode != 0


class DependencyScannerC(DependencyScanner):
    """
    The default C dependency scanner. This is an example on how to implement one.
    Its not perfect so if you have problems feel free to create your own.
    """
    def __init__(self) -> None:
        super().__init__()
    

    def get_dependencies(self, file: str) -> set[str]:
        result: set[str] = set()
        self._scan_file(file, result)
        return result

    
    def _scan_file(self, file: str, result: set[str]) -> None:
        with open(file, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("#include \""):
                    tokens = line.split()
                    dep = tokens[1].strip("\"")
                    path = file[:file.rfind(SLASH) + 1]
                    abs_dep_path = os.path.abspath(f"{path}{dep}")

                    # If it is already in the results then we can skip it. This also avoids dependency cycles.
                    if abs_dep_path in result or not os.path.exists(abs_dep_path):
                        continue

                    result.add(abs_dep_path)
                    self._scan_file(abs_dep_path, result)


class DependencyScannerCPP(DependencyScanner):
    """
    The default C dependency scanner. This is an example on how to implement one.
    Its not perfect so if you have problems feel free to create your own.
    """
    def __init__(self) -> None:
        super().__init__()
    

    def get_dependencies(self, file: str) -> set[str]:
        result: set[str] = set()
        self._scan_file(file, result)
        return result

    
    def _scan_file(self, file: str, result: set[str]) -> None:
        with open(file, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("#include \""):
                    tokens = line.split()
                    dep = tokens[1].strip("\"")
                    path = file[:file.rfind(SLASH) + 1]
                    abs_dep_path = os.path.abspath(f"{path}{dep}")

                    # If it is already in the results then we can skip it. This also avoids dependency cycles.
                    if abs_dep_path in result or not os.path.exists(abs_dep_path):
                        continue

                    result.add(abs_dep_path)
                    self._scan_file(abs_dep_path, result)


def _print_compile_message(mode: str, source: str) -> None:
    match mode:
        case BuildType.DEBUG: print(f"[Info]: building (debug) \"{source}\"")
        case BuildType.RELEASE_FAST: print(f"[Info]: building (release fast) \"{source}\"")
        case BuildType.RELEASE_SAFE: print(f"[Info]: building (release safe) \"{source}\"")
        case BuildType.RELEASE_SMALL: print(f"[Info]: building (release small) \"{source}\"")


class CompilerInvalid(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
        print("[Error]: Could not find a compiler automatically.")
        return False


class CompilerClangC(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file)

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


class CompilerClangCPP(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)
    

    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file)

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


class CompilerGccC(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file)

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


class CompilerGccCPP(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["-c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file)

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


class CompilerMicrosoftC(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def get_object_file_extension(self) -> str:
        return ".obj"

    
    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        print(output)
        common = ["/c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["cl", "/Od", "/Zi", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["cl", "/O2", "/DNDEBUG", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["cl", "/O2", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["cl", "/O1", "/DNDEBUG", f"/Fo{output}", source_file] + params, shell=True).returncode != 0

        return True


class CompilerMicrosoftCPP(Compiler):
    def __init__(self, flags: list[str] = None) -> None:
        super().__init__(flags)


    def get_object_file_extension(self) -> str:
        return ".obj"

    
    def compile_file(self, output_dir: str, output_name: str, source_file: str, build_type: str, flags: list[str]) -> bool:
        output = f"{output_dir}{SLASH}{output_name}"
        common = ["/c"]
        params = common + self.flags + flags

        _print_compile_message(build_type, source_file)

        match build_type:
            case BuildType.DEBUG:
                return subprocess.run(["cl", "/Od", "/Zi", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_FAST:
                return subprocess.run(["cl", "/O2", "/DNDEBUG", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SAFE:
                return subprocess.run(["cl", "/O2", f"/Fo{output}", source_file] + params, shell=True).returncode != 0
            case BuildType.RELEASE_SMALL:
                return subprocess.run(["cl", "/O1", "/DNDEBUG", f"/Fo{output}", source_file] + params, shell=True).returncode != 0

        return True


# Automatic tool detection
DEFAULT_C_COMPILER: Compiler = CompilerInvalid()
DEFAULT_CPP_COMPILER: Compiler = CompilerInvalid()
DEFAULT_LINKER: Linker = LinkerInvalid()
match platform.system():
    case "Windows": 
        if shutil.which("clang") != None:
            DEFAULT_C_COMPILER = CompilerClangC(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerClangExe()
        elif shutil.which("cl") != None:
            DEFAULT_C_COMPILER = CompilerMicrosoftC()
            DEFAULT_LINKER = LinkerMicrosoftExe()
        
        if shutil.which("clang++") != None:
            DEFAULT_CPP_COMPILER = CompilerClangCPP(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerClangExe()
        elif shutil.which("cl") != None:
            DEFAULT_CPP_COMPILER = CompilerMicrosoftCPP()
            DEFAULT_LINKER = LinkerMicrosoftExe()
    
    case "Linux":
        if shutil.which("clang") != None:
            DEFAULT_C_COMPILER = CompilerClangC(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerClangExe()
        elif shutil.which("gcc") != None:
            DEFAULT_C_COMPILER = CompilerGccC(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerGnuExe()

        if shutil.which("clang++") != None:
            DEFAULT_CPP_COMPILER = CompilerClangCPP(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerClangExe()
        elif shutil.which("g++") != None:
            DEFAULT_C_COMPILER = CompilerGccCPP(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerGnuExe()
    
    case "Darwin":
        if shutil.which("clang") != None:
            DEFAULT_C_COMPILER = CompilerClangC(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerClangExe()
        
        if shutil.which("clang++") != None:
            DEFAULT_CPP_COMPILER = CompilerClangCPP(["-Wall", "-Wextra", "-pedantic"])
            DEFAULT_LINKER = LinkerClangExe()


class Languages:
    """
    Preconfigured languages.
    """
    C = Language({".c"}, DependencyScannerC(), DEFAULT_C_COMPILER)
    CPP = Language({".cpp", ".cc"}, DependencyScannerCPP(), DEFAULT_CPP_COMPILER)


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

        if self.files == None:
            self.files = []

        if self.flags == None:
            self.flags = []


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
        linker: Linker = DEFAULT_LINKER
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

        os.makedirs(self._output_path, exist_ok=True)
        os.makedirs(self._object_path, exist_ok=True)


    def add_language(self, language: Language) -> None:
        self._languages.append(language)
    

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
    

    def build(self) -> bool:
        """Builds the project. If the build fails it returns True."""
        self._database.load()

        for path in self._source_paths:
            self._build_source_path(path)

        self._database.save()

        if self._error:
            print("[Error]: Build failed")
            return True

        return False


    def link(self, flags: list[str] = None) -> bool:
        """Links the project. Returns True on failure."""
        if flags == None:
            flags = []

        if self._error:
            return False

        if not self._should_link:
            return False
        
        if self._linker == None:
            print(f"[Error]: No linker available")
            return True
        
        objects: list[str] = []
        objs = self._database.get_objects(self._build_type)
        for obj in objs:
            objects.append(f"{self._object_path}{SLASH}{obj}")
        
        if self._linker.link(self._output_path, self._project_name, self._build_type, objects, flags):
            print("[Error]: Linking failed")
            return True
        
        return False


    def clean_database(self) -> None:
        os.remove(self._database._path)


    def clean_all(self) -> None:
        shutil.rmtree(self._build_path)


    def run_output(self, params: list[str] = None) -> int:
        if params == None:
            params = []
        
        return subprocess.run([f"{self._output_path}{SLASH}{self._project_name}{EXECUTABLE_EXTENSION}"] + params).returncode


    def _build_source_path(self, path: SourcePath) -> None:
        for file in path.files:
            full_file_path = os.path.abspath(f"{path.path}{SLASH}{file}")
            self._build_file(full_file_path, path.flags)
        

    def _build_file(self, file: str, flags: list[str]) -> None:
        source_filename = file[file.rfind(SLASH) + 1:file.rfind(".")]
        source_filepath = file[:file.rfind(SLASH)]

        ext = file[file.rfind("."):]
        flag_str = " ".join(flags)

        language = self._get_language(ext)
        if language == None:
            print(f"[Error]: Source file \"{file}\" is written in an unsupported language")
            self._error = True
            return
        
        if self._error == True:
            return

        obj_prefix = source_filepath.replace(SLASH, "_").replace(":", "_") + "_"
        obj_filename = f"{obj_prefix}{source_filename}{language.compiler.get_object_file_extension()}"
        should_rebuild = False
        
        if not os.path.exists(f"{self._object_path}{SLASH}{obj_filename}"):
            should_rebuild = True
        else:
            data = self._database.query_source(file)
            time_stamp = os.stat(file).st_mtime

            if data == None:
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
            if language.compiler.compile_file(self._object_path, obj_filename, file, self._build_type, flags):
                self._error = True
                return

            self._should_link = True
            deps = language.scanner.get_dependencies(file)
            write_time = os.stat(file).st_mtime
            source_data = _SourceData(deps, write_time, flag_str)
            self._database.update_source(file, source_data)
            self._database.add_object(obj_filename, self._build_type)


    def _get_language(self, ext: str) -> Language:
        for language in self._languages:
            if ext in language.file_extentions:
                return language
        return None
        

class _SourceData:
    def __init__(self, dependencies: list[str] = [], last_write_time: float = 0.0, flags: str = "") -> None:
        self.dependencies = dependencies
        self.last_write_time = last_write_time
        self.flags = flags


class _DatabaseFileContents:
    def __init__(self) -> None:
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