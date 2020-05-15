# yatesim - Yet Another TextEditor and SIMulator
Provides a GUI on Windows for a small simulator. 

## Aim of the project
This project aims to develop a small GUI with as little dependencies as possible for Windows. The GUI includes a text editor in which files can be read and edited, a canvas that automatically interprets the code and draws a circuit, and a text area in which the results of the simulator are displayed. 

## Prerequisites
The following need to be installed on your system for this GUI to work:
- Python 3.6.x , tested on Python 3.6.4 , not sure whether previous Python 3.x work!
- The simulator, which you need to install independently.

You can select the simulator's `.exe` from the GUI, so you don't have to keep the GUI and the simulator in the same folder!

Note also that this GUI builds the circuits on a `tkinter Canvas`, and does not require a LaTeX compiler to be installed on your system. Neither should it require any additional Python packages, as it is built on the `tkinter` package (the Python implementation of `tcl/tk`), which is automatically available from a Python installation.

## Instructions
1. Download this repository and your simulator
2. Run `TextEditor.py` , either from the command line (`cmd -> python TextEditor.py`), or from your favourite Python editor.

User preferences will be stored in `preferences.ini` in the same folder as `TextEditor.py`, so make sure you have write permission for that folder if you want to use preferences.

## No guaranteed cross-platform support
This GUI was specifically designed for Windows. However, in theory `tkinter` should work on MacOS and Linux as well, so feel free to run the GUI on a different platform. You'll have to figure out yourself whether the application works on other platforms. You might have to change some platform-specific code, though ;).

## Todo list
- [ ] Clean up code in `CircuitRender2.py` : classes `GridElement` and `CanvasElem` could actually be merged, much cleaner.
- [x] Using Ctrl+Backspace should also remove consecutive spaces, this does not work with `wordstart` in `tkinter`
- [z] Add shortcut to run the simulator with the current opened file, proposed: `<Ctrl-Return>`. 
- [ ] Allow for separate-window rendering of the circuit just like the simulator output, useful for very large circuits
- [ ] Check for unsaved data during closing of the app, instead of generic warning now
- [ ] Build user-friendly options menu in which text color codes can be changed
- [ ] Interpret the simulator output, perhaps such as highlighting certain sentences

Lower priority:
- [ ] Add dark mode
- [ ] Add autocomplete

## Contact
Please contact me at S.vanPoelgeest@student.tudelft.nl
