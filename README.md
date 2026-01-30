# Screenshot (Clicky)

Aplicativo de captura de tela para desktop com interface GTK.

## Requisitos

- Python 3
- GTK 3 + PyGObject
- Cairo + PyCairo
- GSound (opcional, para som)
- DBus (para integração com GNOME/XDG portal)

No Ubuntu/Debian, o mínimo costuma ser:

```bash
sudo apt-get install -y \
	python3-gi python3-gi-cairo python3-cairo python3-dbus \
	gir1.2-gtk-3.0 gir1.2-gsound-1.0 libgirepository1.0-dev
```

## Executar localmente

```bash
./run_local.sh
```

## CLI

```bash
./clicky_cli.sh --screen
./clicky_cli.sh --window
./clicky_cli.sh --area
```

## Testes

```bash
python3 -m unittest tests/test_basic.py
python3 -m unittest tests/test_logic.py
```

> Observação: os testes dependem de GTK/Cairo. Em ambientes sem GUI, alguns testes são ignorados.
