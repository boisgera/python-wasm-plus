. ${CONFIG:-config}


mkdir -p prebuilt

if [ -d src/pygame-wasm/.git ]
then
    echo "
    * pygame already fetched
"
else
    pushd src
    git clone -b pygame-wasm-upstream https://github.com/pmp-p/pygame-wasm pygame-wasm
    popd
fi



pushd src/pygame-wasm

# regen cython files

#TODO: $HPY setup.py cython config

popd


# active emsdk

. $ROOT/scripts/emsdk-fetch.sh

chmod +x $(find $EMSDK|grep sdl2-config$)


if echo $(which sdl2-config)|grep -q sdl2-config
then
    echo -n
else
    echo "
    =====================================================================
    =====================================================================
    =====================================================================
"

    find $EMSDK|grep sdl2-config$

echo "
    $PATH

    =====================================================================
    =====================================================================
    =====================================================================
"

cat > $HOST_PREFIX/bin/sdl2-config <<END
#!/usr/bin/env python3

import sys

print('emscripten sdl2-config called with', ' '.join(sys.argv), file=sys.stderr)

args = sys.argv[1:]

if '--cflags' in args or '--libs' in args:
  print('-s USE_SDL=2')
elif '--version' in args:
  print('2.0.10')
END

chmod +x $HOST_PREFIX/bin/sdl2-config

fi


pushd src/pygame-wasm

# remove old lib
rm ${ROOT}/prebuilt/libpygame.a

#../../scripts/static-merger.sh

# NB: EMCC_CFLAGS="-s USE_SDL=2 is required to prevent '-iwithsysroot/include/SDL'
# from ./emscripten/tools/ports/__init__.py

# 2>&1 | grep --line-buffered -v DOC_

if python3-wasm setup.py -config -auto -sdl2
then
    if CC=emcc CFLAGS="-DBUILD_STATIC -DSDL_NO_COMPAT -ferror-limit=1"\
 EMCC_CFLAGS="-s USE_SDL=2 -s USE_LIBPNG=1 -s USE_LIBJPEG=1"\
 python3-wasm setup.py build
    then
        OBJS=$(find build/temp.wasm32-tot-emscripten-3.??/|grep o$)
        $EMSDK/upstream/emscripten/emar rcs ${ROOT}/prebuilt/libpygame.a $OBJS
        for obj in $OBJS
        do
            echo $obj
        done
    fi
fi
popd


