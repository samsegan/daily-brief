// The gear menu in the masthead: pick a skin and turn grit on or off.

const { SKINS } = window.briefSkin;

function radio(name, value, label, checked) {
  const input = document.createElement("input");
  input.type = "radio";
  input.name = name;
  input.value = value;
  input.checked = checked;
  const wrapper = document.createElement("label");
  wrapper.className = "segment";
  wrapper.append(input, document.createElement("span"));
  wrapper.lastChild.textContent = label;
  return wrapper;
}

function buildPanel(panel) {
  const { skin, grit } = window.briefSkin.current();
  const skinGroup = document.createElement("fieldset");
  skinGroup.className = "segmented";
  const legend = document.createElement("legend");
  legend.textContent = "Skin";
  skinGroup.append(legend, ...Object.entries(SKINS).map(([id, info]) => radio("skin", id, info.label, id === skin)));

  const gritToggle = document.createElement("label");
  gritToggle.className = "toggle";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.name = "grit";
  checkbox.checked = grit;
  const text = document.createElement("span");
  text.textContent = "Grit: scratches, scanlines, code rain";
  gritToggle.append(checkbox, text);

  panel.replaceChildren(skinGroup, gritToggle);
  panel.addEventListener("change", () => {
    const chosen = panel.querySelector('input[name="skin"]:checked').value;
    window.briefSkin.set(chosen, checkbox.checked);
  });
}

export function mountSettings() {
  const menu = document.getElementById("settings");
  const panel = document.getElementById("settings-panel");
  buildPanel(panel);
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
