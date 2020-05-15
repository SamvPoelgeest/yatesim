import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import tkinter.scrolledtext as tkst
from tkinter import ttk

import subprocess
import time
import configparser

from FileEditor import FileEditor
from CircuitRender2 import CircuitRender

class TextEditor(object):
    '''Holds all the information for an entirely functional GUI.'''
    
    FILETYPES = (('Code Files', '.qc'), ('Text Files', '*.txt'), ('All Files','*.*') )
    
    #Amount of time, in seconds, that we have to wait before we are allowed to re-render a circuit.
    #Adjust this to a higher number if you see that rescaling the window is too slow.
    RENDER_TIME_INTERVAL = 0.5
    
    #Standard configparser file in which we save the preferences
    PREF_FILE_NAME = 'preferences.ini'
    
    def __init__(self, root, output_separate_window=False):
        '''Initializes the TextEditor, using the tkinter window root.
        
        Parameters
        ----------
        output_separate_window: Boolean 
            If true, creates a separate window to run the Simulator, otherwise runs it in the same window.
        '''
        
        self.root = root
        self.output_separate_window = output_separate_window
        
        #Editor frame in which all the editors and the Simulator output is contained
        self.editor_paned_window = None

        
        #We pack both the editor_paned_window and the circuit_frame in the PanedWindow
        self.paned_window = None
        
        #Separate Simulator output window, or a FileEditor output, depending on output_separate_window
        self.runwindow = None
        self.runwindow_text = None
        self.output_file_editor = None
        
        #Amount of files that are currently opened
        self.amount_open = 0
        #File Editors, each containing one file
        self.file_editors = []
        #Active File Editor
        self.active_editor = None
        
        #Circuit canvas frame, circuit builder (a CircuitRenderer) and a circuit canvas
        self.circuit_frame = None
        self.circuit_builder = None
        self.circuit_canvas = None
        
        #Make sure the CircuitRender is not called too often
        self.circuit_render_timeout = -1
        self.circuit_render_scheduled = False
        self.circuit_automatic_render = tk.BooleanVar()
        self.circuit_automatic_render.set(1)
        self.circuit_resize_render = tk.BooleanVar()
        self.circuit_resize_render.set(1)
        
        
        #File path to the Simulator .exe
        self.exe_filename = None
        
        #Menus in the window
        self.menubar = None
        self.filemenu = None
        
        #ConfigParser, which saves user preferences
        self.config_parser = configparser.ConfigParser(allow_no_value=True)
        
        #Initialize the window widgets
        self.init()
        
        #Initialize user preferences
        self.get_preferences()
        
    def init(self) -> None:
        '''Further initializes part of the text editor by building the window widgets'''
        
        ######################## Setup the on-destroy handler
        self.root.protocol("WM_DELETE_WINDOW", self.wants_to_close_program)
        
        ######################## Create the PanedWindow
        self.paned_window = tk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.paned_window.config(sashrelief=tk.RIDGE, sashwidth=10)
        self.paned_window.pack(fill=tk.BOTH, expand=1)
        
        ######################## Create the editor and circuit frame
        self.editor_paned_window = tk.PanedWindow(self.paned_window, orient=tk.HORIZONTAL)
        self.editor_paned_window.config(sashrelief=tk.RIDGE, sashwidth=10)
        self.circuit_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.editor_paned_window)
        self.paned_window.add(self.circuit_frame)
        
        ######################## Create the menu bar
        self.menubar = tk.Menu(self.root, activebackground='skyblue')
        self.root.config(menu=self.menubar)
        
        ######################## Create the file menu
        self.filemenu = tk.Menu(self.menubar, activebackground='skyblue', tearoff=0 )
        
        #Add newfile command, openfile command, savefile command, etc.
        self.filemenu.add_command(label='New File', accelerator='Ctrl+N', command=lambda: self.newfile())
        self.filemenu.add_command(label='Open File', accelerator='Ctrl+O', command=lambda: self.openfile())
        self.filemenu.add_command(label='Save File', accelerator='Ctrl+S', command=lambda: self.savefile())
        self.filemenu.add_command(label='Save File As', accelerator='Ctrl+Shift+S', command=lambda: self.savefileas())
        self.filemenu.add_separator()
        self.filemenu.add_command(label='Exit', command=self.exit)
        self.menubar.add_cascade(label='File', menu=self.filemenu)
        
        ######################## Create the setup menu
        self.setupmenu = tk.Menu(self.menubar, activebackground='skyblue', tearoff=0 )
        
        self.setupmenu.add_command(label='Setup Simulator.exe', command=self.set_exe_filename)
        self.setupmenu.add_command(label='Toggle output mode', command=self.toggle_output_mode)
        self.setupmenu.add_checkbutton(label='Automatic circuit rendering', onvalue=1, offvalue=0, variable=self.circuit_automatic_render)
        self.setupmenu.add_checkbutton(label='Rerender circuit on resize', onvalue=1, offvalue=0, variable=self.circuit_resize_render)
        self.menubar.add_cascade(label='Options', menu=self.setupmenu)
        
        ######################## Create the circuit builder
        self.circuit_canvas = tk.Canvas(self.circuit_frame,\
                                        width=int(self.circuit_frame.winfo_width()), \
                                        height=int(self.circuit_frame.winfo_height()), background='white' )
        self.circuit_canvas.pack(fill=tk.BOTH, expand=1)
        
        self.circuit_builder = CircuitRender(self.circuit_canvas)
        
        self.circuit_canvas.bind('<Configure>', self.canvas_resize )
        
        ######################## Build the runwindow, or alternatively the output_file_editor
        self.build_output()
        
    def build_output(self) -> None:
        '''Builds the output widget, either a disabled FileEditor or a separate window.'''
        
        if self.output_separate_window:
            self.runwindow = tk.Toplevel(root)
            self.runwindow.title('Simulator Output Window')
            #Delay the setting of the geometry, as the geometry of the root might not yet be updated.
            self.runwindow.after(100, lambda : self.runwindow.geometry(self.root.winfo_geometry()) )
            self.runwindow_text = tk.Text(self.runwindow)
            self.runwindow_text.pack(fill=tk.BOTH, expand=1)
            #Make sure that if this window is destroyed, we toggle to the different output mode inside the main window
            self.runwindow.protocol("WM_DELETE_WINDOW", self.toggle_output_mode)
        else:
            #Build a disabled FileEditor
            self.output_file_editor = FileEditor(self, self.editor_paned_window, self.amount_open)
            self.output_file_editor.txtarea.configure(state='disabled')
            self.output_file_editor.title.set('Simulator Output')
            self.output_file_editor.closebutton.grid_forget()
            self.output_file_editor.runbutton.grid_forget()
            self.output_file_editor.buildbutton.grid_forget()
            
            self.editor_paned_window.add(self.output_file_editor.frame, minsize=100)
            self.editor_paned_window.paneconfig(self.output_file_editor.frame, minsize=0)
        
    def toggle_output_mode(self,*args) -> None:
        '''Toggles the output mode between a disabled FileEditor and a new window
        
        Parameters
        ----------
        *args : object
            Specifically added such that event handler that automatically pass along an event object can call this function
        '''
        
        if self.output_separate_window:
            self.runwindow.destroy()
            self.runwindow = None
        else:
            self.output_file_editor.frame.grid_forget()
            self.output_file_editor.frame.destroy()
            self.output_file_editor = None
        
        self.output_separate_window = not self.output_separate_window
        self.build_output()
        
    def newfile(self) -> None:
        '''Opens a new FileEditor with an Untitled text file.'''
        
        self.amount_open += 1
        
        fe = FileEditor(self, self.editor_paned_window, self.amount_open-1)
        #Add the FileEditor to the editor_paned_window
        self.add_to_editor_paned_window(fe.frame)
        
        self.file_editors.append( fe )
        self.active_editor = fe
        
    def add_to_editor_paned_window(self, child, minsize=300) -> None:
        '''Adds a FileEditor (child) to the Editor PanedWindow, and sets the appropriate minsize.
        
        Parameters
        ----------
        
        child : tkinter widget
            widget (usually a tk.Frame) that has to be added to the editor_paned_window
        minsize = 300  : integer
            minimum size of the child when added to the editor_paned_window, afterwards directly set to 0 to make
            sure user can resize to any size.
        '''
        
        if self.output_separate_window:
            self.editor_paned_window.add(child, minsize=minsize)
        else:
            self.editor_paned_window.add(child, before=self.output_file_editor.frame, minsize=minsize)
        
        self.editor_paned_window.paneconfig(child, minsize=0)
        
    def openfile(self,filename=None, suppress=True) -> None:
        '''Opens a FileEditor with a file that is selected by the user
        
        Parameters
        ----------
        
        filename = None : r-string
            String literal containing the file path
        suppress = True : Boolean
            Suppresses errros whilst opening a file.
        '''
        
        #Remove focus from the current element
        self.root.focus()
        
        file = None
        
        try:
            if filename is None:
                filename = filedialog.askopenfilename(title='Select file', filetypes=self.FILETYPES )
            
            if filename:
                file = open(filename,'r')
        except Exception as e:
            if not suppress:
                messagebox.showerror('Exception', e)
            return
            
        if file is None:
            if not suppress:
                messagebox.showerror('Exception', 'File is None')
            return
        
        #File will be closed by FileEditor as soon as it has read out the file.
        self.amount_open += 1
        fe = FileEditor(self, self.editor_paned_window, self.amount_open -1, filename = filename, file = file)
        #Add the FileEditor to the editor_paned_window
        self.add_to_editor_paned_window(fe.frame)
            
        self.file_editors.append( fe )
        self.active_editor = fe
        
    def savefile(self, suppress=False) -> bool:
        '''Saves the text in the active_editor to storage. If name is unspecified, this calls savefileas().
        
        Parameters
        ----------
        
        suppress = False : Boolean
            Suppresses error messages if set to True.
        '''
        
        #Check whether we have an active file that we are trying to save:
        if not self.active_editor:
            if not suppress:
                messagebox.showerror('Exception', 'There is no self.active_editor!')
            return False
    
        #Find the active editor
        fe = self.active_editor
        
        #Check whether the active editor is actually an Untitled file, then we need saveas:
        if not fe.filename:
            return self.savefileas()
        
        #Get data, and try to write this to the file.
        data = fe.txtarea.get('1.0', tk.END)
        
        try:
            outfile = open(fe.filename,'w')
            outfile.write(data)
            outfile.close()
        except Exception as e:
            if not suppress:
                messagebox.showerror('Exception',e)
            return False
            
        #Update the fe to let the user know the save was successful
        fe.save_was_successful()
        
        return True
    
    def savefileas(self, suppress=True) -> bool:
        '''Saves the text in the active_editor to storage, and asks the user in which file to store.
        
        Parameters
        ----------
        
        suppress = True : Boolean
            Suppresses error messages if set to True.
        '''
        
        #Remove focus from the current element
        self.root.focus()
        
        #Check whether we have an active file that we are trying to save:
        if not self.active_editor:
            if not suppress:
                messagebox.showerror('Exception', 'There is no self.active_editor!')
            return False
        
        #Find the active editor
        fe = self.active_editor
        
        try:
            filename = filedialog.asksaveasfilename(title='Save File As...', defaultextension='.qc', initialfile='untitled.qc',\
                                               filetypes=self.FILETYPES)
            data = fe.txtarea.get('1.0', tk.END)
            
            outfile = open(filename,'w')
            outfile.write(data)
            outfile.close()
        except Exception as e:
            if not suppress:
                messagebox.showerror('Exception', e )
            return False
            
        #Update the fe title name
        fe.set_filename(filename)
        
        return True
    
    #TODO: implement methods that keep track whether there are unsaved changes.
    def exit(self,*args) -> None:
        '''Exits the editor after asking for permission.
        
        Parameters
        ----------
        *args : object
            Specifically added such that event handler that automatically pass along an event object can call this function
        '''
        
        if messagebox.askyesno('WARNING','Unsaved data might be lost!'):
            self.root.destroy()
            
    def canvas_resize(self,*args) -> None:
        '''Event handler that is called when the canvas gets resized.
                
        Parameters
        ----------
        *args : object
            Specifically added such that event handler that automatically pass along an event object can call this function
        '''
        #If the user does not want us to act on this
        if not self.circuit_resize_render.get():
            return
        
        #Only allow for a redraw once per time interval
        if time.time() > self.circuit_render_timeout:
            self.circuit_render_timeout = time.time() + self.RENDER_TIME_INTERVAL
            self.circuit_render_scheduled = False
            self.root.after(int(self.RENDER_TIME_INTERVAL*1000), self.async_canvas_resize)
            
        #This call was too soon, but we reschedule it to the new time interval
        elif not self.circuit_render_scheduled:
            #print('Rescheduling canvas_resize')
            self.circuit_render_scheduled = True
            self.circuit_canvas.after( int( (self.circuit_render_timeout - time.time())*1000 ), self.canvas_resize )
            
    def async_canvas_resize(self):
        '''Re-renders the circuit_canvas, called from the canvas_resize method'''
        try:
            self.circuit_builder.render()
        except Exception as e:
            pass
    
    def set_active_editor(self, fe) -> None:
        '''Set the active_editor to fe
        
        Parameters
        ----------
        
        fe : FileEditor
            The FileEditor that will become the active editor.
        '''
        self.active_editor = fe
    
    def wants_to_close(self, fe) -> bool:
        '''Attempt to close an open FileEditor.
        
        Parameters
        ----------
        
        fe : FileEditor
            The FileEditor that should be closed.
        
        Output
        ------
        Boolean, denoting successful closure (True) or no closure (False)
        '''
        #TODO: implement methods that keep track whether there are unsaved changes.
        if messagebox.askyesno('Close file?',f'Are you sure you want to close {fe.filename}?'):
            if self.active_editor == fe:
                self.active_editor = None
                
            self.file_editors.remove(fe)
            self.amount_open -= 1
            return True
        return False
    
    def set_exe_filename(self,*args) -> bool:
        '''Sets the path to the simulator .exe file
        
        Parameters
        ----------
        *args : object
            Specifically added such that event handler that automatically pass along an event object can call this function
        '''
        
        filename = None
        
        try:
            filename = filedialog.askopenfilename(title='Select Simulator.exe' )
        except Exception as e:
            messagebox.showerror('Exception', e)
            return False
        
        if filename:
            self.exe_filename = filename
            return True
        
        return False
    
    def write_preferences(self, set_=False) -> None:
        '''Attempts to write the user preferences through the configparser
        
        Parameters
        ----------
        set_ = False : Boolean
            If True, we will first attempt to create the preferences before storing them.
        '''
        
        if set_:
            self.set_preferences()
        
        try:
            configfile = open(self.PREF_FILE_NAME,'w')
            self.config_parser.write(configfile)
        except Exception as e:
            messagebox.showerror('Exception in ConfigParser', e)
    
    def set_preferences(self) -> None:
        '''Sets all the user preferences, but does NOT write them to file yet.'''
        
        #Save the .exe file path
        if self.exe_filename:
            self.config_parser['EXE DIRECTORY'] = {'dir': self.exe_filename }
        
        #Save a list of currently opened files with a name
        if self.amount_open > 0:
            named_editors = [fe for fe in self.file_editors if fe.filename]
            self.config_parser['OPENED FILES'] = { idx : fe.filename for idx,fe in enumerate(named_editors) }
            
        #Save the preference of running the simulator in a separate window or in a FileEditor
        self.config_parser['RUNNING PREFERENCE'] = {'separate_window' : self.output_separate_window }
        
        #Automatic rendering of the circuit
        self.config_parser['RENDERING PREFERENCES'] = { 'circuit_automatic_render' : self.circuit_automatic_render.get() == 1,
                                                        'circuit_resize_render' : self.circuit_resize_render.get() == 1 }
            
    def get_preferences(self) -> None:
        '''Attempts to get the user preferences through the configparser'''
        try:
            self.config_parser.read(self.PREF_FILE_NAME)
            
            #Set the .exe file path
            if 'EXE DIRECTORY' in self.config_parser:
                if 'dir' in self.config_parser['EXE DIRECTORY']:
                    self.exe_filename = self.config_parser['EXE DIRECTORY']['dir']
                    
            #Open saved files
            if 'OPENED FILES' in self.config_parser:
                for idx in self.config_parser['OPENED FILES']:
                    #self.root.after_idle(lambda: self.openfile( \
                    #        filename=self.config_parser['OPENED FILES'][idx], suppress=True ) )
                    self.openfile(filename=self.config_parser['OPENED FILES'][idx], suppress=True )
                    
            #Change preference of running the simulator in a separate window
            if 'RUNNING PREFERENCE' in self.config_parser:
                if 'separate_window' in self.config_parser['RUNNING PREFERENCE']:
                    if self.config_parser.getboolean('RUNNING PREFERENCE','separate_window') != self.output_separate_window:
                        self.toggle_output_mode()
                        
            #Set the automatic rendering of the circuit
            if 'RENDERING PREFERENCES' in self.config_parser:
                if 'circuit_automatic_render' in self.config_parser['RENDERING PREFERENCES']:
                    self.circuit_automatic_render.set(\
                        1 if self.config_parser.getboolean('RENDERING PREFERENCES','circuit_automatic_render') else 0 )
                if 'circuit_resize_render' in self.config_parser['RENDERING PREFERENCES']:
                    self.circuit_resize_render.set( \
                        1 if self.config_parser.getboolean('RENDERING PREFERENCES','circuit_resize_render') else 0)
                    
        except Exception as e:
            messagebox.showerror('Exception in ConfigParser', e)
        
        
    
    def run_file(self, filename) -> bool:
        '''Attempts to run a .qc file from the FileEditor
        
        Parameters
        ----------
        filename : string
            Contains the path to the file.
        '''
        
        if not self.exe_filename:
            if not self.set_exe_filename():
                messagebox.showerror('Exception', 'No exe filename has been set!')
                return False
        

        result = subprocess.run([self.exe_filename,filename], stdout=subprocess.PIPE).stdout.decode('utf-8')
        
        if self.output_separate_window:
            text_widget = self.runwindow_text
        else:
            text_widget = self.output_file_editor.txtarea
            text_widget.configure(state='normal')
        
        text_widget.delete(1.0,tk.END)
        for line in result.split('\n'):
            text_widget.insert(tk.END, line+'\n')
        
        if not self.output_separate_window:
            self.output_file_editor.txtarea.configure(state='disabled')
            
        return True
            
    def build_circuit(self, suppress=False, from_keypress=False) -> None:
        '''Builds the circuit, using the active file editor
        
        Parameters
        ----------
        suppress = False : Boolean
            Suppresses the error messages
        from_keypress = False : Boolean
            If this build_circuit call came from a Return button press
        '''
        
        #If the user does not want us to act on this
        if from_keypress and self.circuit_automatic_render.get() == 0:
            return
        
        self.root.after(int(self.RENDER_TIME_INTERVAL*1000), lambda: self.async_build_circuit(suppress=suppress))
        
    def async_build_circuit(self, suppress=False):
        '''Builds the circuit, using the active file editor
        
        Parameters
        ----------
        suppress = False : Boolean
            Suppresses the error messages
        '''
        try:
            fe = self.active_editor
            data = fe.txtarea.get('1.0', tk.END)
            self.circuit_builder.read(data)
            self.circuit_builder.render()
        except Exception as e:
            if not suppress:
                messagebox.showerror('Exception',e)
                
    def wants_to_close_program(self,*args) -> None:
        '''Runs when the user wants to close the window using the red cross
        
        Parameters
        ----------
        *args : object
            Specifically added such that event handler that automatically pass along an event object can call this function
        '''
        if self.amount_open > 0:
            if messagebox.askokcancel("Quit", "You have open files! Do you want to quit?"):
                self.write_preferences(set_=True)
                self.root.destroy()
        else:
            self.write_preferences(set_=True)
            self.root.destroy()
            
            

if __name__ == '__main__':
    #Create the window
    root = tk.Tk()
    root.title('Simulator Text Editor')

    #Find the width and height of the computer screen
    max_width, max_height = root.winfo_screenwidth(), root.winfo_screenheight()
    #Make the window half the size of the computer screen, and center it
    root.geometry(f'{int(3*max_width/4)}x{int(3*max_height/4)}+{int(max_width/8)}+{int(max_height/8)}')
    
    TextEditor(root, output_separate_window=False)
    root.lift()
    root.attributes('-topmost',True)
    root.after_idle(root.attributes,'-topmost',False)
    root.mainloop()  