# Instalación siguiendo las convenciones de GNU/Linux.
#   sudo make install                    # en /usr/local
#   make install PREFIX=/usr DESTDIR=pkg # para empaquetadores (staging)

APP          := ds4-volante
PYTHON       ?= python3
PREFIX       ?= /usr/local
BINDIR       ?= $(PREFIX)/bin
LIBDIR       ?= $(PREFIX)/lib/$(APP)
DATADIR      ?= $(PREFIX)/share
MANDIR       ?= $(DATADIR)/man
# udev y systemd no leen /usr/local, así que por defecto se usa /etc.
# Los paquetes de distribución pueden usar /usr/lib/udev/rules.d y /usr/lib/modules-load.d.
UDEVRULESDIR   ?= /etc/udev/rules.d
MODULESLOADDIR ?= /etc/modules-load.d

INSTALL      ?= install
FUENTES      := $(wildcard src/ds4_volante/*.py)

.PHONY: all run test install uninstall recargar-udev clean

all:
	@echo "Objetivos: run, test, install, uninstall, clean"

run:
	PYTHONPATH=src $(PYTHON) -m ds4_volante

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

install:
	$(INSTALL) -d $(DESTDIR)$(LIBDIR)/ds4_volante
	$(INSTALL) -m 644 $(FUENTES) $(DESTDIR)$(LIBDIR)/ds4_volante/
	$(INSTALL) -d $(DESTDIR)$(BINDIR)
	printf '#!/bin/sh\nPYTHONPATH="%s$${PYTHONPATH:+:$$PYTHONPATH}"\nexport PYTHONPATH\nexec %s -m ds4_volante "$$@"\n' \
		'$(LIBDIR)' '$(PYTHON)' > $(DESTDIR)$(BINDIR)/$(APP)
	chmod 755 $(DESTDIR)$(BINDIR)/$(APP)
	$(INSTALL) -Dm 644 data/$(APP).desktop $(DESTDIR)$(DATADIR)/applications/$(APP).desktop
	$(INSTALL) -Dm 644 data/$(APP).svg $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APP).svg
	$(INSTALL) -Dm 644 docs/$(APP).1 $(DESTDIR)$(MANDIR)/man1/$(APP).1
	$(INSTALL) -Dm 644 data/70-$(APP).rules $(DESTDIR)$(UDEVRULESDIR)/70-$(APP).rules
	$(INSTALL) -Dm 644 data/$(APP)-modules.conf $(DESTDIR)$(MODULESLOADDIR)/$(APP).conf
	@if [ -z "$(DESTDIR)" ]; then $(MAKE) --no-print-directory recargar-udev; fi

uninstall:
	rm -f $(DESTDIR)$(LIBDIR)/ds4_volante/*.py
	rm -rf $(DESTDIR)$(LIBDIR)/ds4_volante/__pycache__
	-rmdir $(DESTDIR)$(LIBDIR)/ds4_volante $(DESTDIR)$(LIBDIR)
	rm -f $(DESTDIR)$(BINDIR)/$(APP) \
	      $(DESTDIR)$(DATADIR)/applications/$(APP).desktop \
	      $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APP).svg \
	      $(DESTDIR)$(MANDIR)/man1/$(APP).1 \
	      $(DESTDIR)$(UDEVRULESDIR)/70-$(APP).rules \
	      $(DESTDIR)$(MODULESLOADDIR)/$(APP).conf

# Aplica las reglas sin reiniciar. Después, vuelve a conectar el control.
recargar-udev:
	-modprobe uinput
	-udevadm control --reload-rules
	-udevadm trigger --subsystem-match=misc --subsystem-match=input
	@echo "Listo. Desconecta y vuelve a conectar el control."

clean:
	rm -rf build dist src/ds4_volante.egg-info .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -r {} +
