#!/bin/bash

# ATENCIÓN: receta NO soportada en bauh Gekko Edition.
#
# Tal y como está, descarga y empaqueta el código del proyecto ORIGINAL
# (vinifmor/bauh), no el de este fork, y el AppImage resultante se
# auto-actualizaría contra las releases del upstream. Se conserva solo como
# referencia histórica; habría que reescribirla entera para revivirla.
#
# El canal soportado es install.sh + pipx.
if [ "${BAUH_APPIMAGE_UNSUPPORTED_OK:-}" != "1" ]; then
    echo "[bauh] linux_dist/appimage no está soportado: construiría el bauh original, no este fork." >&2
    echo "[bauh] Se conserva solo como referencia histórica. Si aun así quieres ejecutarlo:" >&2
    echo "[bauh]   BAUH_APPIMAGE_UNSUPPORTED_OK=1 BAUH_VERSION=... bash build.sh" >&2
    exit 1
fi

set -Ceuo pipefail

docker build -t bauh-appimage .
docker run -e BAUH_VERSION="$BAUH_VERSION" -v ./AppImageBuilder.yml:/build/AppImageBuilder.yml --rm --cap-add=SYS_ADMIN --device /dev/fuse --mount type=bind,source="$(pwd)",target=/build bauh-appimage
# volume required to run tests: -v /var/run/docker.sock:/var/run/docker.sock
