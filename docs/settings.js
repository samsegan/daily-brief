// The gear menu in the masthead: pick a skin and switch its effects on or off.

const { SKINS, CHANGE_EVENT } = window.briefSkin;

function radio(name, value, label, checked) {
  const input = document.createElement("input");
  input.type = "radio";
  input.name = name;
  input.value = value;
  input.checked = checked;
  const text = document.createElement("span");
  text.textContent = label;
  const wrapper = document.createElement("label");
  wrapper.className = "segment";
  wrapper.append(input, text);
  return wrapper;
}

function buildPanel(panel) {
  const { skin, fx } = window.briefSkin.current();
  const skinGroup = document.createElement("fieldset");
  skinGroup.className = "segmented";
  const legend = document.createElement("legend");
  legend.textContent = "Skin";
  skinGroup.append(legend, ...Object.entries(SKINS).map(([id, info]) => radio("skin", id, info.label, id === skin)));

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.name = "fx";
  checkbox.checked = fx;
  const fxText = document.createElement("span");
  const fxToggle = document.createElement("label");
  fxToggle.className = "toggle";
  fxToggle.append(checkbox, fxText);

  // The switch is named for what the current skin's effects are; Paper has none.
  const relabel = () => {
    const { fxLabel } = SKINS[window.briefSkin.current().skin];
    fxText.textContent = fxLabel;
    fxToggle.hidden = !fxLabel;
  };
  relabel();
  document.addEventListener(CHANGE_EVENT, relabel);

  panel.replaceChildren(skinGroup, fxToggle);
  panel.addEventListener("change", () => {
    const chosen = panel.querySelector('input[name="skin"]:checked').value;
    window.briefSkin.set(chosen, checkbox.checked);
  });
}

export function mountSettings() {
  const menu = document.getElementById("settings");
  buildPanel(document.getElementById("settings-panel"));
  // Close on outside click or Escape, like a native menu.
  document.addEventListener("click", (event) => {
    if (menu.open && !menu.contains(event.target)) menu.open = false;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menu.open) {
      menu.open = false;
      menu.querySelector("summary").focus();
    }
  });
}
