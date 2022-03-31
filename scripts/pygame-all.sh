
. ${CONFIG:-config}

if [[ ! -z ${EMSDK+z} ]]
then
    echo -n
else
    . scripts/emsdk-fetch.sh
fi

echo "
    * emsdk ready in $EMSDK
"

cat > $ROOT/${PYDK_PYTHON_HOST_PLATFORM}-shell.sh <<END
#!/bin/bash
export PATH=${HOST_PREFIX}/bin:$PATH
export PKG_CONFIG_PATH=${PKG_CONFIG_PATH}
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
export HOME=${PYTHONPYCACHEPREFIX}
export PLATFORM_TRIPLET=${PYDK_PYTHON_HOST_PLATFORM}
export PREFIX=$PREFIX

export PYTHONSTARTUP="${ROOT}/support/__EMSCRIPTEN__.py"
> ${PYTHONPYCACHEPREFIX}/.pythonrc.py

export PS1="[PyDK:wasm] \w $ "

export _PYTHON_SYSCONFIGDATA_NAME=_sysconfigdata__emscripten_

if [[ ! -z \${EMSDK+z} ]]
then
    # emsdk_env already parsed
    echo -n
else
    pushd $ROOT
    . scripts/emsdk-fetch.sh
    popd
fi
END

cat > $HOST_PREFIX/bin/python3-wasm <<END
#!/bin/bash
. $ROOT/${PYDK_PYTHON_HOST_PLATFORM}-shell.sh

# to fix non interactive startup
#touch $HOST_PREFIX/__main__.py

cat >${PYTHONPYCACHEPREFIX}/.numpy-site.cfg <<NUMPY
[DEFAULT]
library_dirs = $PREFIX//lib
include_dirs = $PREFIX/include
NUMPY

# so include dirs are good
export PYTHONHOME=$PREFIX

# but still can load dynload and setuptools
export PYTHONPATH=$(echo -n ${HOST_PREFIX}/lib/python3.??/lib-dynload):$(echo -n ${HOST_PREFIX}/lib/python3.??/site-packages)

#probably useless
export _PYTHON_HOST_PLATFORM=${PYDK_PYTHON_HOST_PLATFORM}
export PYTHON_FOR_BUILD=${PYTHON_FOR_BUILD}

$HOST_PREFIX/bin/python3 -u -B \$@
END

chmod +x $HOST_PREFIX/bin/python3-wasm

mkdir -p prebuilt

if [ -d src/pygame-wasm ]
then
    echo "
    * pygame already fetched
"
else
    pushd src
    git clone -b pygame-wasm https://github.com/pmp-p/pygame-wasm pygame-wasm
    popd
fi

pushd src/pygame-wasm

# remove old lib
rm ${ROOT}/prebuilt/libpygame.a

# regen cython files
python3 setup.py cython config

# NB: EMCC_CFLAGS="-s USE_SDL=2 is required to prevent '-iwithsysroot/include/SDL'
# from ./emscripten/tools/ports/__init__.py



if python3-wasm setup.py -config -auto -sdl2
then
    if CC=emcc CFLAGS="-DBUILD_STATIC -DSDL_NO_COMPAT -ferror-limit=1"\
 EMCC_CFLAGS="-s USE_SDL=2 -s USE_LIBPNG=1 -s USE_LIBJPEG=1"\
 python3-wasm setup.py build
    then
        OBJS=$(find build/temp.wasm32-tot-emscripten-3.??/|grep o$)
        llvm-ar rcs ${ROOT}/prebuilt/libpygame.a $OBJS
        for obj in $OBJS
        do
            echo $obj
        done
    fi
fi
popd



