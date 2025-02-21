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


echo "



    *******************************************************************************
    *******************************************************************************





"

cat emsdk/upstream/emscripten/emcc

echo "



    *******************************************************************************
    *******************************************************************************





"


pushd src/pygame-wasm

# regen cython files

#TODO: $HPY setup.py cython config

popd


#chmod +x $(find $EMSDK|grep sdl2-config$)


pushd src/pygame-wasm

# remove old lib
[ -f ${ROOT}/prebuilt/libpygame.a ] && rm ${ROOT}/prebuilt/libpygame.a

# emsdk is activated via python3-wasm

if python3-wasm setup.py -config -auto -sdl2
then
    if CC=emcc CFLAGS="-DBUILD_STATIC -DSDL_NO_COMPAT -ferror-limit=1 -fPIC"\
 EMCC_CFLAGS="-s USE_SDL=2 -sUSE_LIBPNG -s USE_LIBJPEG -sUSE_SDL_TTF -sUSE_SDL_IMAGE"\
 python3-wasm setup.py build
    then
        OBJS=$(find build/temp.wasm32-tot-emscripten-3.??/|grep o$)
        $ROOT/emsdk/upstream/emscripten/emar rcs ${ROOT}/prebuilt/libpygame.a $OBJS
        for obj in $OBJS
        do
            echo $obj
        done
    fi
fi
popd


