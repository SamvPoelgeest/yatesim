import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import tkinter.scrolledtext as tkst
from tkinter import ttk

class FileEditor(object):
    '''FileEditor: class that describes one single opened text editor file.'''
    MENU_FONT = 'Courier 12 bold'
    TEXT_FONT = 'Courier 10'
    SAVE_SUCCESSFUL_TIMEOUT = 2000
    
    HIGHLIGHT_KEYWORDS=  ('h','x','y','z', 'rx','ry','rz','s','ph', 't','tdag', 'cnot', 'cx', 'c-x', 'toffoli',\
                          'prepz', 'measure','not','swap','cphase','cz','c-z','cr','map')
    
    def __init__(self, texteditor, paned_window, column, filename = None, file = None):
        '''Initializes the FileEditor. 
        
        Parameters
        ----------
        texteditor : TextEditor
            The TextEditor that this FileEditor is a part of
        paned_window : tk.PanedWindow
            The PanedWindow that this FileEditor is a part of
        column : integer
            The column number that this FileEditor occupies
        filename = None : string
            The path to the file that this FileEditor displays
        file = None : File
            The file that this FileEditor will display
        '''
        
        self.texteditor = texteditor
        self.paned_window = paned_window
        self.column = column
        self.filename = filename
        self.short_filename = None
        
        #Further initialize
        self.init(file=file)
        
        #Set up the event handling
        self.setup_event_handling()
        
    def init(self, file=None):
        '''Further initializes the FileEditor
        
        Parameters
        ----------
        file = None : File
            The file that this FileEditor will read and display.
        '''
        
        self.frame = tk.Frame(self.paned_window)
        
        self.title = tk.StringVar()
        
        self.titlebar = ttk.Label(self.frame, textvariable = self.title, borderwidth=2)#, relief=tk.GROOVE)
        self.titlebar.grid(row=0, column=0, sticky='nesw')
        
        self.closebutton = ttk.Button(self.frame, text='[X]', command=self.close)
        self.closebutton.grid(row=0,column=1,sticky='nesw')
        
        self.runbutton = ttk.Button(self.frame, text='Run', command=self.run_file)
        self.runbutton.grid(row=0,column=2, sticky='nesw')
        
        self.buildbutton = ttk.Button(self.frame, text='Build', command=lambda: self.build_circuit(suppress=False))
        self.buildbutton.grid(row=0,column=3, sticky='nesw')
        
        self.txtarea = tkst.ScrolledText( master=self.frame, wrap = 'none', font=self.TEXT_FONT, state='normal', relief=tk.GROOVE )
        self.txtarea.grid(row=1,column=0, columnspan=4, sticky='nesw')
        
        #Set title to filename if available
        if self.filename:
            self.set_filename(self.filename)
        else:
            self.title.set('Untitled')
            
        #Set highlighter tag configs
        self.highlighter_set_configs()
            
        #Read file if available
        if file:
            try:
                for line in file:
                    self.txtarea.insert(tk.END, line)
            except Exception as e:
                messagebox.showerror('Exception', e)
                return
            self.highlighter(all_=True)
            
        self.frame_configure()
            
    def frame_configure(self):
        '''Configures the relative widths of the different columns of the FileEditor'''
        
        self.frame.grid_columnconfigure(0, weight=9)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_columnconfigure(2, weight=1)
        self.frame.grid_columnconfigure(3, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)
        
    def update_column(self,column):
        '''Updates the current column in which the FileEditor is displayed
        
        Parameters
        ----------
        column : integer
            The new column index.
        '''
        self.column = column
        self.frame.grid(row=0,column=self.column, sticky='nsew')
        
    def run_file(self,*args):
        '''Runs the file that is opened in the FileEditor
        
        *args : object
            Specifically added such that event handlers that automatically pass along an event object can call this function
        '''
        
        #First, set this FileEditor to the active editor
        self.texteditor.set_active_editor(self)
        #Then, attempt to save this file so unsaved changes are used as well
        self.texteditor.savefile()
        
        #If we still do not have a filename, we cannot attempt to run this file
        if not self.filename:
            messagebox.showerror('Error!', 'Attempting to run file, but the filename has not been set. Strange!')
            return
        
        #Run the file through the TextEditor.
        self.texteditor.run_file(self.filename)
        
    def build_circuit(self,suppress=False, from_keypress=False, *args):
        '''Builds the circuit
        
        Parameters
        ----------
        suppress = False : Boolean
            Suppresses error messages
        from_keypress = False : Boolean
            Set to True if this build_circuit call came from a user Key-event.
        *args : object
            Specifically added such that event handler that automatically pass along an event object can call this function
        '''
        #First, set this FileEditor to the active editor
        self.texteditor.set_active_editor(self)
        #Now, pass it to the TextEditor
        self.texteditor.build_circuit(suppress=suppress, from_keypress=from_keypress)
                
    def save_was_successful(self):
        '''Triggered when the TextEditor announces this file was successfully saved.'''
        
        old_title = self.short_filename if self.short_filename else 'Untitled'
        self.title.set('Saved successfully!')
        self.paned_window.after(self.SAVE_SUCCESSFUL_TIMEOUT, lambda : self.title.set(old_title))
        
    def set_filename(self, new_filename):
        '''Sets the filename of this FileEditor
        
        Parameters
        ----------
        new_filename : string
            Contains the new path to the file.
        '''
        
        self.filename = new_filename
        self.short_filename = self.filename.split('/')[-1]
        self.title.set(self.short_filename)
        
    def setup_event_handling(self):
        '''Sets up all the event handling that this FileEditor does. '''
        #Handle the shortcuts
        
        #We need to break after the shortcuts to remove unwanted built-in tkinter input handling.
        def call_and_break(func):
            def bind_func(*args):
                func()
                return 'break'
            return bind_func
        
        self.txtarea.bind('<Control-n>', call_and_break( self.texteditor.newfile))
        self.txtarea.bind('<Control-o>', call_and_break(  self.texteditor.openfile))
        self.txtarea.bind('<Control-s>', call_and_break( self.texteditor.savefile))
        self.txtarea.bind('<Control-Shift-S>', call_and_break(  self.texteditor.savefileas))
        self.txtarea.bind('<Control-Return>', call_and_break( self.build_circuit ))
        self.txtarea.bind('<Control-Shift-Return>', call_and_break( self.run_file ))
        
        #Handle the highlighter
        for x in range(ord('a'), ord('z')+1):
            self.txtarea.bind(f'<KeyRelease-{chr(x)}>', lambda e: self.highlighter(all_=False))
        others = ('1','2','3','4','5','6','7','8','9','0','-','=',',','space')
        for x in others:
            self.txtarea.bind(f'<KeyRelease-{x}>', lambda e: self.highlighter(all_=False))

        def ctrlv(*args):
            self.txtarea.after(100, lambda: self.highlighter(all_=True))
        self.txtarea.bind('<Control-v>', ctrlv)
        
        #Handle a <tab>
        def tab(*args):
            #print('Tab called!')
            self.txtarea.insert(tk.INSERT, ' '*4 )
            return 'break'
        self.txtarea.bind('<Tab>', tab)
        
        #Handle <Ctrl-BackSpace>
        def ctrl_backspace(*args):
            #print('Ctrl+Backspace called!')
            #This does not work with spaces: self.txtarea.delete(f'{tk.INSERT} -1c wordstart', tk.INSERT)
            row = self.txtarea.index(tk.INSERT).split('.')[0]
            #Get the text from the row
            line = self.txtarea.get(row+'.0', tk.INSERT)
            
            #If this is an empty line, do a normal backspace
            if len(line) == 0:
                return
            
            #If we're in a word or at the end of a word
            if line[-1].isalnum():
                idx = 2
                while idx <= len(line) and line[-idx].isalnum():
                    idx += 1
                self.txtarea.delete(f'{tk.INSERT} - {idx-1}c', tk.INSERT)
            #Otherwise, remove the spaces before this
            elif line[-1] == ' ':
                idx = 2
                while idx <= len(line) and line[-idx] == ' ':
                    idx += 1
                self.txtarea.delete(f'{tk.INSERT} - {idx-1}c', tk.INSERT)
            else: #Otherwise, destroy one special character by NOT returning 'break'
                return
            
            #Do NOT remove extra characters
            return 'break'
        self.txtarea.bind('<Control-BackSpace>', ctrl_backspace)
        
        #Handle the focus
        self.txtarea.bind('<FocusIn>', lambda e: self.texteditor.set_active_editor(self))
        
        #Handle automatic builder
        def return_button(event):
            #Only use the return button if it is NOT used in combination with Ctrl or Ctrl+Shift
            if event.state in (4,5): #4 = Ctrl, 5 = Ctrl+Shift
                return
            
            #Rebuild the circuit
            self.build_circuit(suppress=True, from_keypress=True)
            #If we are in a subroutine, automatically add spaces
            row = int( self.txtarea.index(tk.INSERT).split('.')[0] )
            #print(f"::{self.txtarea.get(f'{row-1}.0', f'{row-1}.1')}::")
            if row > 1 and self.txtarea.get(f'{row-1}.0', f'{row-1}.1') in (' ','.'):
                self.txtarea.insert(f'{tk.INSERT} linestart', ' '*4)
        self.txtarea.bind('<KeyRelease-Return>', return_button )
        
        #Handle multi-line comment
        def multiline_comment(*args):
            #print('Multiline-comment called!')
            #Get the first and last line from the selection
            restore_selection = self.txtarea.tag_ranges(tk.SEL)
            
            if self.txtarea.tag_ranges(tk.SEL):       
                row_first = int( self.txtarea.index(tk.SEL_FIRST).split('.')[0] )
                row_last = int( self.txtarea.index(tk.SEL_LAST).split('.')[0] )
            else:
                row_first = int( self.txtarea.index(tk.INSERT).split('.')[0] )
                row_last = row_first
                
            for row in range(row_first,row_last+1):
                line = self.txtarea.get(str(row)+'.0', str(row)+'.end')
                #If we have to uncomment the line
                if len(line.lstrip()) > 0 and line.lstrip()[0] == '#':
                    comment_index = line.index('#')
                    self.txtarea.delete(str(row)+'.'+str(comment_index), str(row)+'.'+str(comment_index+1))
                #If we have to comment the line
                else:
                    self.txtarea.insert(str(row)+'.0','#')
            
            self.txtarea.tag_remove(tk.SEL, '1.0', tk.END)
            if restore_selection:
                self.txtarea.tag_add(tk.SEL, *restore_selection)
            
            self.highlighter(all_=True)
            return 'break'
                
        self.txtarea.bind('<Control-slash>', multiline_comment)

        
    def highlighter(self, all_=False):
        '''Highlights the relevant parts of the code.
        
        Parameters
        ----------
        all_ = False : Boolean
            Set to True if you want the entire content of the FileEditor to redo the highlighting. Is too slow for long files.
        '''
        if all_:
            start_row = 1
            end_row = int( self.txtarea.index('end-1c').split('.')[0])
        else:
            start_row = int( self.txtarea.index(tk.INSERT).split('.')[0])
            end_row = start_row
            
        def analyze_line(line, offset=0):
            nonlocal row, row_end
            
            def str_idx(idx):
                nonlocal row, offset
                return str(row)+'.'+str(idx+offset)
            
            #Is this line a white line? Continue
            if len(line.strip()) == 0:
                return
                
            #Get the comment index if it exists
            if '#' in line:
                comment_index = line.index('#')
                #print(f'Adding tag comment, {str_idx(comment_index)}, {row_end}')
                self.txtarea.tag_add('comment', str_idx(comment_index), row_end)
                
                line = line[0:line.index('#')]
                
                if len(line) == 0:
                    return
                    
            if 'display' in line:
                display_index = line.index('display')
                #self.txtarea.tag_add('display',str(row)+'.'+str(display_index), str(row)+'.'+str(display_index+len('display')))
                #Update: make the entire line this style, it might be a display_something namely.
                self.txtarea.tag_add('display',str_idx(display_index), str_idx(len(line)))
                return
            
            if 'qubits' in line:
                self.txtarea.tag_add('qubits',str_idx(0), str_idx(len(line)))
                return
            
            if line[0] == '.':
                end_idx = line.index('(') if '(' in line else len(line)
                self.txtarea.tag_add('subroutine', str_idx(0), str_idx(end_idx))
            
            if '|' in line:
                lines = line.split('|')
                curr_offset = offset
                for subline in lines:
                    #print(f'Analyzing subline {subline} with offset {curr_offset}!')
                    analyze_line(subline, offset=curr_offset)
                    curr_offset += len(subline)+1 #+1 for the '|' itself!
                    
                indices = [i for i,x in enumerate(line) if x=='|']
                for idx in indices:
                    self.txtarea.tag_add('bracket', str_idx(idx), str_idx(idx+1))
            
            for bracket in ('{', '}', '(', ')'):
                if bracket in line:
                    idx = line.index(bracket)
                    self.txtarea.tag_add('bracket', str_idx(idx), str_idx(idx+1))
                    
            for keyword in self.HIGHLIGHT_KEYWORDS:
                if keyword in line.lower():
                    idx = line.lower().index(keyword)
                    self.txtarea.tag_add(keyword, str_idx(idx), str_idx(idx+len(keyword)))
                
                
            
        for row in range(start_row,end_row+1):
            #Convert to tkinter indices
            row_start = self.txtarea.index(str(row)+'.0')
            row_end   = self.txtarea.index(str(row)+'.end')
            
            #Remove all previous tags on this line
            for tag in self.txtarea.tag_names():
                #Update: do NOT remove selections!
                if tag == tk.SEL:
                    continue
                self.txtarea.tag_remove(tag, row_start, row_end)
            
            #Get the text from the row
            line = self.txtarea.get(row_start, row_end)
            
            #Analyze the text: this borrows from CircuitRender2.Circuitrender.read()
            analyze_line(line)
                
        
    def highlighter_set_configs(self):
        '''Sets the specific colours for the different tags used in the highlighter.'''
        self.txtarea.tag_config('comment', foreground='gray')
        self.txtarea.tag_config('display', foreground='DarkOrange3')
        self.txtarea.tag_config('bracket', foreground='DarkOrange3')
        self.txtarea.tag_config('qubits', foreground='purple')
        self.txtarea.tag_config('subroutine',foreground='purple')
        for keyword in self.HIGHLIGHT_KEYWORDS:
            self.txtarea.tag_config(keyword, foreground='purple')
        
    def close(self):
        '''Attempt to close this FileEditor.'''
        if self.texteditor.wants_to_close(self):
            self.frame.grid_forget()
            self.frame.destroy()
    