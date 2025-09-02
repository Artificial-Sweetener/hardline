# Hardline

This is **Hardline**, a tiny Tkinter GUI application designed to help you fix your ComfyUI workflows when Set/Get nodes go rogue!

The latest version of ComfyUI has unfortunately introduced a breaking change that affects the beloved Set/Get nodes from [KJNodes](https://github.com/kijai/ComfyUI-KJNodes) (see [Issue #366](https://github.com/kijai/ComfyUI-KJNodes/issues/366_)). This can leave your carefully crafted workflows in a bind. Hardline steps in to help you get back on track by rewiring those broken Set/Get connections into direct, hardcoded links.

It's a simple, portable solution to keep your workflows running smoothly while we all hope for a patch! This way, you can keep working in the older version of ComfyUI front-end that still works with set/get nodes (1.24.4) and then use this little doo-dad to provide compatible versions for your users that are on the updated version.

<p align="center"><img width="725" height="435" alt="image" src="https://github.com/user-attachments/assets/3a749cb1-6864-4a45-88cc-6ef1a27d7974" /></p>


## Installation

Hardline is designed to be super easy to use with no external dependencies beyond standard Python libraries. The Sun Valley theme is optional and will be used if `sv-ttk` is installed.

**Quick start:**
1. Download the `hardline.exe` executable from the [releases page](https://github.com/Artificial-Sweetener/hardline/releases).
2. Run it!

If you prefer to run from source:
1. Clone this repository.
2. Ensure you have Python 3.x installed.
3. Run `hardline.py` directly:
   ```bash
   python hardline.py
   ```

## Usage

1. **Input JSON:** Select your ComfyUI workflow JSON file.
2. **Output JSON:** Choose where to save the rewired workflow. By default, it will suggest `<input_filename>_hardline.json`.
3. **Drop Set/Get nodes:** Optionally, you can choose to remove the Set/Get nodes from the workflow after they've been rewired.
4. **Convert!**

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. Please see the `LICENSE` file for full details.

## From the Developer ❤️

I made this little tool because I know how frustrating it can be when your creative tools break. My hope is that Hardline helps you keep your ComfyUI workflows flowing without interruption. We're all in this together!

- **Buy Me a Coffee**: You can help fuel more projects like this at my [Ko-fi page](https://ko-fi.com/artificial_sweetener).
- **My Website & Socials**: See my art, poetry, and other dev updates at [artificialsweetener.ai](https://artificialsweetener.ai).
- **If you like this project**, it would mean a lot to me if you gave me a star here on Github!! ⭐
