UI_DIR = assets/qt
PY_DIR = ui

$(PY_DIR)/%.py: $(UI_DIR)/%.ui
	pyuic5 -x $< -o $@

# Define targets to convert all .ui files
UI_FILES := $(wildcard $(UI_DIR)/*.ui)
PY_FILES := $(patsubst $(UI_DIR)/%.ui, $(PY_DIR)/%.py, $(UI_FILES))

ui: $(PY_FILES)

# Clean up generated .py files
clean:
	rm -f $(PY_FILES)