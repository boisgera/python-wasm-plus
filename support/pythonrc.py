#!pythonrc.py

import os, sys, json, builtins

# to be able to access aio.cross.simulator
import aio
import aio.cross


# the sim does not preload assets and cannot access currentline
# unless using https://github.com/pmp-p/aioprompt/blob/master/aioprompt/__init__.py

if not defined('undefined'):
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

    define("undefined", sentinel())
    del sentinel


    define('false', False)
    define('true', True)

    # fix const without writing const in that .py because of faulty micropython parser.
    exec("__import__('builtins').const = lambda x:x", globals(), globals())


def overloaded(i, *attrs):
    for attr in attrs:
        if attr in vars(i.__class__):
            if attr in vars(i):
                return True
    return False


builtins.overloaded = overloaded


try:
    # mpy already has execfile
    execfile
except:
    def execfile(filename):
        global pgzrun

        imports = []

        with __import__('tokenize').open(filename) as f:
            __prepro = []
            myglobs = ['setup', 'loop', 'main']
            tmpl = []

            pgzrun = None

            for l in f.readlines():
                if pgzrun is None:
                    pgzrun = l.find('pgzrun')>0

                testline = l.split('#')[0].strip(" \r\n,\t")

                if testline.startswith('global ') and (
                        testline.endswith(' setup')
                        or
                        testline.endswith(' loop')
                        or
                        testline.endswith(' main')
                    ):
                        tmpl.append( [len(__prepro),l.find('g')] )
                        __prepro.append("#globals")
                        continue
                elif testline.startswith('import '):
                    testline = testline.replace('import ','').strip()
                    imports.extend( map(str.strip, testline.split(',') ) )
                elif testline.startswith('from '):
                    testline = testline.replace('from ','').strip()
                    imports.append( testline.split(' import ')[0].strip() )


                __prepro.append(l)

                if l[0] in ("""\n\r\t'" """):
                    continue

                if not l.find('=')>0:
                    continue

                l = l.strip()

                if l.startswith('def '):
                    continue
                if l.startswith('class '):
                    continue

                #maybe found a global assign
                varname = l.split('=',1)[0].strip(" []()")

                for varname in map(str.strip, varname.split(',') ):

                    if varname.find(' ')>0:
                        continue

                    #it's a comment on an assign !
                    if varname.find('#')>=0:
                        continue

                    #skip attr assign
                    if varname.find('.')>0:
                        continue

                    # not a tuple assign
                    if varname.find('(')>0:
                        continue

                    # not a list assign
                    if varname.find('[')>0:
                        continue

                    #TODO handle (a,)=(0,) case types

                    if not varname in myglobs:
                        myglobs.append(varname)

            myglob = f"global {', '.join(myglobs)}\n"

            for mark, indent in tmpl:
                __prepro[mark] = ' '*indent + myglob


            def dump_code():
                nonlocal __prepro
                print()
                print("_"*70)
                for i,l in enumerate(__prepro):
                    print(str(i).zfill(5),l , end='')
                print("_"*70)
                print()

            #if aio.cross.simulator:
            #    dump_code()

            # use of globals() is only valid in __main__ scope
            # we really want the module __main__ dict here
            # whereever from we are called.

            __main__dict = vars(__import__("__main__"))
            __main__dict['__file__']= filename
            try:
                code = compile("".join(__prepro), filename, "exec")
            except SyntaxError as e:
                #if not aio.cross.simulator:
                dump_code()
                sys.print_exception(e)
                code=None

            if code:
                if pgzrun:
                    sys.argv.append(filename)
                    import pgzero
                    import pgzero.runner
                    print("*"*40)
                    print(imports)
                    print("*"*40)
                    pgzero.runner.main()
                else:
                    exec( code, __main__dict, __main__dict )
        return __import__("__main__")


    define('execfile', execfile)

if defined('embed') and hasattr(embed,'readline'):

    class shell:
        if aio.cross.simulator:
            ROOT = os.getcwd()
            HOME = os.getcwd()
        else:
            ROOT = f"/data/data/{sys.argv[0]}"
            HOME = f"/data/data/{sys.argv[0]}/assets"


        @classmethod
        def cat(cls, *argv):
            for fn in argv:
                with open(fn,'r') as out:
                    print( out.read() )

        @classmethod
        def ls(cls, *argv):
            if not len(argv):
                argv=['.']
            for arg in argv:
                for out in os.listdir(arg):
                    print(out)

        @classmethod
        def mkdir(cls, *argv):
            exist_ok = '-p' in argv
            for arg in argv:
                if arg == '-p':
                    continue
                os.makedirs(arg, exist_ok=exist_ok)


        @classmethod
        def pwd(cls, *argv):
            print( os.getcwd())

        @classmethod
        def cd(cls, *argv):
            if len(argv):
                os.chdir( argv[-1] )
            else:
                os.chdir( cls.HOME )
            print('[ ',os.getcwd(),' ]')


    def excepthook(etype, e, tb):
        global last_fail

        catch = False

        if isinstance(e, NameError):
            catch = True

        if catch or isinstance(e, SyntaxError) and e.filename == "<stdin>":
            catch = True
            #index = readline.get_current_history_length()


            #asyncio.get_event_loop().create_task(retry(index))
            # store trace
            #last_fail.append([etype, e, tb])

            cmdline = embed.readline().strip()
            first = True
            for cmd in cmdline.strip().split(';'):
                cmd = cmd.strip()
                if cmd.find(' ')>0:
                    cmd, args = cmd.split(' ',1)
                    args = args.split(' ')
                else:
                    args = ()

                if hasattr(shell, cmd):
                    try:
                        getattr(shell, cmd)(*args)
                    except Exception as cmderror:
                        print(cmderror, file=sys.stderr)
                elif cmd.endswith('.py'):
                    execfile(cmd)
                else:
                    catch =False
                first = False

        if not catch:
            sys.__excepthook__(etype, e, tb)
        else:
            embed.prompt()

    sys.excepthook = excepthook





try:
    PyConfig
    aio.cross.simulator = ( __EMSCRIPTEN__ or __wasi__ or __WASM__).PyConfig_InitPythonConfig( PyConfig )
#except NameError:
except Exception as e:
    sys.print_exception(e)
#   TODO: get a pyconfig from C here
#    <vstinner> pmp-p: JSON au C : connais les API secrète
# _PyConfig_FromDict(), _PyInterpreterState_SetConfig() et _testinternalcapi.set_config()?
#    <vstinner> pmp-p: j'utilise du JSON pour les tests unitaires sur PyConfig dans test_embed

    PyConfig = {}
    print(" - running in simulator - ")
    aio.cross.simulator = True

# make simulations same each time, easier to debug
import random
random.seed(1)

#======================================================


#
