#!/bin/sh
# Desinstala la versión 0.1 de ds4-volante (instalación manual en ~/Apps).
#
# Elimina solo los archivos conocidos de esa versión:
#   - ds4-volante.py, ds4-volante, askpass-yad y __pycache__ en la carpeta
#     de instalación (por defecto ~/Apps/ds4-volante);
#   - lanzadores .desktop, enlaces y scripts del usuario que apunten a esa carpeta.
# Copia la configuración antigua a la ubicación nueva y conserva la original.
# No modifica la versión nueva instalada con «make install».

set -eu

PROG=$(basename "$0")
CARPETA="$HOME/Apps/ds4-volante"
SIMULAR=0
CONFIRMADO=0

uso() {
    cat <<EOF
Uso: $PROG [opciones]

Desinstala la versión 0.1 de ds4-volante del usuario actual.

Opciones:
  -d, --dir RUTA   carpeta de la versión 0.1 (por defecto: ~/Apps/ds4-volante)
  -n, --simular    muestra lo que se haría, sin cambiar nada
  -y, --si         no pide confirmación
  -h, --help       muestra esta ayuda
EOF
}

aviso() { printf '%s: %s\n' "$PROG" "$*" >&2; }
error() { aviso "error: $*"; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        -d|--dir)
            [ $# -ge 2 ] || error "falta la ruta después de $1"
            CARPETA=$2; shift ;;
        --dir=*) CARPETA=${1#*=} ;;
        -n|--simular) SIMULAR=1 ;;
        -y|--si) CONFIRMADO=1 ;;
        -h|--help) uso; exit 0 ;;
        *) uso >&2; error "opción desconocida: $1" ;;
    esac
    shift
done

if [ "$(id -u)" -eq 0 ]; then
    error "ejecútalo como tu usuario normal, sin sudo (la versión 0.1 está en tu carpeta personal)."
fi

# Ruta absoluta y sin barra final, para buscar referencias.
case "$CARPETA" in /*) ;; *) CARPETA="$PWD/$CARPETA" ;; esac
CARPETA=${CARPETA%/}

CONFIG_BASE=${XDG_CONFIG_HOME:-$HOME/.config}
case "$CONFIG_BASE" in /*) ;; *) CONFIG_BASE="$HOME/.config" ;; esac
DATOS_BASE=${XDG_DATA_HOME:-$HOME/.local/share}
case "$DATOS_BASE" in /*) ;; *) DATOS_BASE="$HOME/.local/share" ;; esac
CONFIG_ANTIGUA="$CONFIG_BASE/ds4-volante.json"
CONFIG_NUEVA="$CONFIG_BASE/ds4-volante/config.json"

# Lista de elementos a eliminar (una ruta por línea).
LISTA=$(mktemp)
trap 'rm -f "$LISTA"' EXIT INT TERM
agregar() { printf '%s\n' "$1" >> "$LISTA"; }

# 1. Archivos de la carpeta de instalación.
CARPETA_ES_GIT=0
if [ -d "$CARPETA/.git" ]; then
    CARPETA_ES_GIT=1
elif [ -d "$CARPETA" ]; then
    for archivo in ds4-volante.py ds4-volante askpass-yad; do
        if [ -f "$CARPETA/$archivo" ] || [ -L "$CARPETA/$archivo" ]; then
            agregar "$CARPETA/$archivo"
        fi
    done
    if [ -d "$CARPETA/__pycache__" ]; then
        agregar "$CARPETA/__pycache__"
    fi
fi

# 2. Lanzadores, accesos directos y scripts que apunten a la carpeta antigua.
ESCRITORIO=$(xdg-user-dir DESKTOP 2>/dev/null || true)
for dir in "$DATOS_BASE/applications" "$CONFIG_BASE/autostart" \
           "${ESCRITORIO:-$HOME/Desktop}" "$HOME/Escritorio"; do
    [ -d "$dir" ] || continue
    for archivo in "$dir"/*.desktop; do
        [ -f "$archivo" ] || continue
        if grep -qF "$CARPETA" "$archivo" 2>/dev/null; then
            agregar "$archivo"
        fi
    done
done

for dir in "$HOME/.local/bin" "$HOME/bin"; do
    [ -d "$dir" ] || continue
    for archivo in "$dir"/*; do
        if [ -L "$archivo" ]; then
            case "$(readlink "$archivo")" in
                "$CARPETA"/*) agregar "$archivo" ;;
            esac
        elif [ -f "$archivo" ] && [ "$(wc -c < "$archivo")" -lt 4096 ] &&
             grep -qF "$CARPETA" "$archivo" 2>/dev/null; then
            agregar "$archivo"
        fi
    done
done

# --- Resumen --------------------------------------------------------------
MIGRAR=0
if [ -f "$CONFIG_ANTIGUA" ] && [ ! -e "$CONFIG_NUEVA" ]; then
    MIGRAR=1
fi

if [ ! -s "$LISTA" ] && [ "$MIGRAR" -eq 0 ]; then
    echo "No se encontraron restos de la versión 0.1 en $CARPETA."
    if [ "$CARPETA_ES_GIT" -eq 1 ]; then
        echo "Esa carpeta es un clon de git; no se modifica (ver más abajo)."
    fi
fi

if [ -s "$LISTA" ]; then
    echo "Se eliminarán:"
    sed 's/^/  /' "$LISTA"
fi
if [ "$MIGRAR" -eq 1 ]; then
    echo "Se copiará la configuración:"
    echo "  $CONFIG_ANTIGUA -> $CONFIG_NUEVA"
fi

if [ "$CARPETA_ES_GIT" -eq 1 ]; then
    cat <<EOF

Nota: $CARPETA es un clon de git, así que no se borra nada dentro.
Puedes actualizarlo e instalar la versión nueva desde ahí:
  git -C "$CARPETA" pull && sudo make -C "$CARPETA" install
o borrarlo tú mismo si ya clonaste el proyecto en otra carpeta.
EOF
fi

if [ ! -s "$LISTA" ] && [ "$MIGRAR" -eq 0 ]; then
    exit 0
fi

if [ "$SIMULAR" -eq 1 ]; then
    echo
    echo "Modo simulación: no se hizo ningún cambio."
    exit 0
fi

if [ "$CONFIRMADO" -eq 0 ]; then
    [ -t 0 ] || error "no hay terminal para confirmar; usa --si para continuar sin preguntar."
    printf '\n¿Continuar? [s/N] '
    read -r respuesta || respuesta=
    case "$respuesta" in
        s|S|si|SI|Si|sí|Sí|SÍ) ;;
        *) echo "Cancelado. No se hizo ningún cambio."; exit 1 ;;
    esac
fi

# --- Ejecución ------------------------------------------------------------
if [ "$MIGRAR" -eq 1 ]; then
    mkdir -p "$(dirname "$CONFIG_NUEVA")"
    cp -p "$CONFIG_ANTIGUA" "$CONFIG_NUEVA"
    echo "Configuración copiada (la original se conserva en $CONFIG_ANTIGUA)."
fi

while IFS= read -r ruta; do
    if [ -d "$ruta" ] && [ ! -L "$ruta" ]; then
        rm -r -- "$ruta"
    else
        rm -f -- "$ruta"
    fi
    echo "Eliminado: $ruta"
done < "$LISTA"

if [ "$CARPETA_ES_GIT" -eq 0 ] && [ -d "$CARPETA" ]; then
    if rmdir -- "$CARPETA" 2>/dev/null; then
        echo "Eliminada la carpeta vacía: $CARPETA"
    else
        echo "La carpeta $CARPETA contiene otros archivos; se conserva."
    fi
fi

if command -v update-desktop-database >/dev/null 2>&1 &&
   [ -d "$DATOS_BASE/applications" ]; then
    update-desktop-database "$DATOS_BASE/applications" 2>/dev/null || true
fi

echo
echo "Versión 0.1 desinstalada."
if ! command -v ds4-volante >/dev/null 2>&1; then
    echo "Para instalar la versión nueva, ejecuta «sudo make install» en la carpeta del proyecto."
fi
