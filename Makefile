all: $(patsubst assets/qt/%.ui, ui/%.py, $(wildcard assets/qt/*.ui))

ui/%.py: assets/qt/%.ui
	pyuic5 -x $< -o $@
