# builtins.__EMSCRIPTEN__
# builtins.__WASI__
# builtins.__ANDROID__   also defines __ANDROID_API__
# builtins.__UPY__
# can point to this module

import sys, os, builtins

# are they not ?
builtins.builtins = builtins


try:
    import aio
except Exception as e:
    try:
        sys.print_exception(e)
    except:
        __import__("traceback").print_exc()

    # non asyncio stepper as a fallback
    class aio:
        paused = False
        steps = []
        oneshots = []
        ticks = 0
        protect = []

        @classmethod
        def breakpointhook(cls, *argv, **kw):
            cls.paused = True

        @classmethod
        def step(cls):
            if cls.paused:
                return

            if aio.protect:
                aio.protect.clear()

            try:
                # NEED a scheduler + timesort
                early = []
                while len(cls.oneshots):
                    deferred = cls.oneshots.pop()
                    if deferred[0] > cls.ticks:
                        deferred[0] -= 1
                        early.append(deferred)
                    else:
                        _, fn, argv, kw = deferred
                        fn(*argv, **kw)
                while len(early):
                    cls.oneshots.append(early.pop())

                for step in cls.steps:
                    step()
            except Exception as e:
                sys.print_exception(e)
                cls.paused = True
                pdb("- aio paused -")

        @classmethod
        def defer(cls, fn, argv=(), kw={}, deadline=0):
            # FIXME: set ticks + deadline for alarm
            cls.oneshots.append(
                [
                    cls.ticks + deadline,
                    fn,
                    argv,
                    kw,
                ]
            )


def breakpointhook(*argv, **kw):
    aio.paused = True


sys.breakpointhook = breakpointhook

define("aio", aio)


this = __import__(__name__)

# those  __dunder__ are usually the same used in C conventions.


try:
    __UPY__
except:
    if hasattr(sys.implementation, "mpy"):
        builtins.__UPY__ = this
    else:
        builtins.__UPY__ = None

try:
    __EMSCRIPTEN__
except:
    if sys.platform in ("emscripten", "asm.js", "wasm"):
        builtins.__EMSCRIPTEN__ = this
    else:
        builtins.__EMSCRIPTEN__ = None

try:
    __WASI__
except:
    if sys.platform in (
        "wasm",
        "wasi",
    ):
        builtins.__WASI__ = this
    else:
        builtins.__WASI__ = None

try:
    __ANDROID__
except:
    # this *is* the cpython way
    if hasattr(sys, "getandroidapilevel"):
        builtins.__ANDROID__ = this
        builtins.__ANDROID_API__ = sys.getandroidapilevel()
    else:
        builtins.__ANDROID__ = False


# force use a fixed, tested version of uasyncio to avoid non-determinism
if __UPY__:
    sys.modules["sys"] = sys
    sys.modules["builtins"] = builtins
    try:
        from . import uasyncio as uasyncio

        print("Warning : using WAPY uasyncio")
    except Exception as e:
        sys.print_exception(e)

else:
    try:
        from . import uasyncio_cpy as uasyncio
    except:
        pdb("INFO: no uasyncio implementation found")
        uasyncio = aio

sys.modules["uasyncio"] = uasyncio


# this should be done in site.py / main.c but that's not so easy.
# last chance to do it since required by aio.*
try:
    undefined
except:

    class sentinel:
        def __bool__(self):
            return False

        def __repr__(self):
            return "∅"

        def __nonzero__(self):
            return 0

        def __call__(self, *argv, **kw):
            if len(argv) and argv[0] is self:
                return True
            print("Null Pointer Exception")

    sentinel = sentinel()
    builtins.undefined = sentinel
    del sentinel


def overloaded(i, *attrs):
    for attr in attrs:
        if attr in i.__class__.__dict__:
            if attr in i.__dict__:
                return True
    return False


builtins.overloaded = overloaded


def init_platform(embed):
    # simulator won't run javascript for now
    if not hasattr(embed, "run_script"):
        pdb("186: no js engine")
        return False

    import json

    def js(code, delay=0):
        # keep a ref till next loop
        aio.protect.append(code)
        if not delay:
            result = embed.run_script(f"JSON.stringify({code})")
            if result is not None:
                return json.loads(result)
        elif delay < 0:
            embed.run_script(code)
        else:
            embed.run_script(code, int(delay))

    embed.js = js


    if __WASM__:
        import _thread

        try:
            _thread.start_new_thread(lambda: None, ())
        except RuntimeError:
            pdb("WARNING: that wasm build does not support threads")



def PyConfig_InitPythonConfig(PyConfig):
    global preloadedWasm, preloadedImages, preloadedAudios

    # simulator won't run javascript for now
    if not hasattr(embed, "run_script"):
        pdb("209: no js engine")
        return False

    # do not do stuff if not called properly from our js loader.
    if PyConfig.get("executable", None) is None:
        # running in sim
        return False

    sys.executable = PyConfig["executable"]

    import shutil

    preloadedWasm = "so"
    preloadedImages = "png jpeg jpg gif"
    preloadedAudios = "wav ogg mp4"

    def preload(p=None):
        global preload, prelist, ROOTDIR, preloadedWasm, preloadedImages, preloadedAudios
        ROOTDIR = p or f"/data/data/{sys.argv[0]}"
        if os.path.isdir(ROOTDIR):
            os.chdir(ROOTDIR)
        else:
            pdb(f"cannot chdir to {ROOTDIR=}")
            return

        ROOTDIR = os.getcwd()
        LSRC = len(ROOTDIR) + 1
        counter = 0
        prelist = {}

        def explore(pushpopd, newpath):
            global prelist, preloadedWasm, preloadedImages, preloadedAudios
            nonlocal counter

            if newpath.endswith(".git"):
                return

            for dirname, dirnames, filenames in os.walk(newpath):
                try:
                    os.chdir(dirname)
                    # print(f"\nNow in {os.getcwd()[LSRC:] or '.'}")

                except:
                    print("Invalid Folder :", pushpopd, newpath)

                for f in filenames:
                    if not os.path.isfile(f):
                        continue

                    ext = f.rsplit(".", 1)[-1].lower()

                    if (
                        ext.lower()
                        not in f"{preloadedImages} {preloadedAudios} {preloadedWasm}"
                    ):
                        continue

                    src = os.path.join(os.getcwd(), f)
                    dst = "/tmp/pre" + str(counter).zfill(4) + "." + ext
                    shutil.copyfile(src, dst)
                    prelist[src] = dst
                    embed.preload(dst)
                    counter += 1

                for subdir in dirnames:
                    explore(os.getcwd(), subdir)

            os.chdir(pushpopd)

        if os.path.isdir("assets"):
            explore(ROOTDIR, "assets")
            os.chdir(f"{ROOTDIR}/assets")
        else:

            embed.prompt()
        print(f"assets found :", counter)

        sys.path.insert(0, os.getcwd())
        return True

    import aio.clock

    # force start asyncio.run is not blocking on that platform.
    aio.clock.start(x=80)

    # org.python no preload !

    if (sys.argv[0] != 'org.python') and preload():

        def fix_preload_table():
            global aio, prelist, preloadedWasm, preloadedImages, preloadedAudios

            if embed.counter() < 0:
                pdb("asset manager not ready 0>", embed.counter())
                aio.defer(fix_preload_table, deadline=60)
            else:
                pdb("all assets were ready at", embed.counter())

            for (
                src,
                dst,
            ) in prelist.items():
                ext = dst.rsplit(".", 1)[-1]
                if ext in preloadedImages:
                    ptype = "preloadedImages"
                elif ext in preloadedAudios:
                    ptype = "preloadedAudios"
                elif ext == "so":
                    ptype = "preloadedWasm"

                src = f"{ptype}[{repr(src)}]"
                dst = f"{ptype}[{repr(dst)}]"
                swap = f"({src}={dst}) && delete {dst}"
                embed.js(swap, -1)
                # print(swap)

            if os.path.isfile("main.py"):
                def runmain(py):
                    __main__ = execfile(py)
                    if not aio.started:
                        print("333: TODO setup+loop autostart")
                        # __main__.setup()
                        # aio.steps.append(__main__.loop)
                        # aio.started = True

                print(f"320: running {sys.argv[0]}.py as main (deferred)")
                aio.defer(runmain, ["main.py"])
            else:
                pdb(f"no main found for {sys.argv[0]}")

        # C should unlock aio loop when preload count reach 0.
        aio.defer(fix_preload_table, deadline=60)
    else:
        def fix_preload_table():
            pdb("no assets preloaded")
        print()
        embed.prompt()

    # go pods !
    aio.started = True


