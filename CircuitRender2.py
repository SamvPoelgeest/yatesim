import tkinter as tk
from tkinter.font import Font
import re

class CircuitRender(object):
    '''CircuitRender renders the circuit of the code inside a tkinter canvas'''
    
    #The standard fonts that will be used in chronological order.
    STD_FONTS = [ {'family':'Bookman Old Style', 'size':14},\
              {'family':'Century', 'size':14}, \
              {'family':'Courier', 'size':14}]
    
    #The rendering margins on the canvas
    RENDER_MARGINS = {'w':5, 'h':5}
    
    #Possible statements, and the amount of arguments expected after the statement
    POSS_STATEMENTS = {'h':1, 'x':1, 'y':1, 'z':1, 'rx':2, 'ry':2, 'rz':2, 's':1, 'ph':1, 't':1, 'tdag':1, \
                      'cnot':2, 'cx':2, 'c-x':2, 'toffoli':3, 'swap':2, 'cphase':2, 'cz':2,'c-z':2,'cr':2,\
                       'prepz':1 , 'measure':0, 'not':1, 'map':2 }
    #Possible statements that have a variable amount of arguments, POSS_STATEMENTS then gives the minimum
    POSS_STATEMENTS_EXCEPT = ('cx','c-x','cz','c-z','measure')
    
    #Collection of all the operations that are single-qubit gates
    SINGLE_QUBIT_GATES = ('h','x','y','z', 'rx','ry','rz','s','ph', 't','tdag', 'prepz', 'measure','not')
    #Collection of all the operations that are multiple-qubit gates
    MULTIPLE_QUBIT_GATES = ('cnot','cx','c-x','toffoli','swap','cphase','cz','cr')
    
    def __init__(self, canvas):
        '''Initializes the CircuitRender: needs a canvas.'''
        
        #Keep track of the canvas on which we draw 
        self.canvas = canvas
        
        #Keep track of the amount of qubits in the circuit
        self.nr_qubits = -1
        #Keep track of the names of the qubits and classical bits, assigned through the 'map' command
        #will always have len(...) = 2 * self.nr_qubits, set through the .read(...) method
        self.channel_names = []
        
        #Keep track of the entire grid that is updated in read(...). Each element represents a ROW
        #Elements in self.grid are dictionaries, keys are COLUMNs, and values are GridElements.
        self.grid = []
        #Keep track of the total amount of columns, calculated by read(...)
        self.max_col = -1
        
        #Keep track of the subroutines in the data
        self.subroutines = []
        
        #Keep track of font used to render
        self.font = None
        
    def render(self):
        '''Renders the circuit to the self.canvas'''
        
        #First, remove everything from the canvas
        self.canvas.delete('all')

        if not self.font:
            self.build_font()
        
        #Set the width and height of the drawing area
        width = int(self.canvas.winfo_width()) - self.RENDER_MARGINS['w']
        height = int(self.canvas.winfo_height()) - self.RENDER_MARGINS['h']
        #Fall back on original width and height if the previous numbers are nonsensical
        if width <= 1 or height <= 1:
            width = int(self.canvas.cget('width')) - self.RENDER_MARGINS['w']
            height = int(self.canvas.cget('height')) - self.RENDER_MARGINS['h']
            
        #To determine nr of rows, first determine which classical bits might not be in use
        classical_bits_in_use = [len(self.grid[x]) > 0 for x in range(self.nr_qubits,2*self.nr_qubits)]
        
        #Keep track of which classical bits to display. This acts as grid_row = to_gridrow[draw_row].
        to_gridrow = [x for x in range(self.nr_qubits)] + \
                        [x+self.nr_qubits for x in range(self.nr_qubits) if classical_bits_in_use[x] ]
        
        #We need an extra column to display the initial names, and an extra row if we have subroutines
        extra_row = len(self.subroutines) > 0
        nr_cols = self.max_col+1
        nr_rows = self.nr_qubits + sum(classical_bits_in_use) + extra_row
        
        #Produce the first naming col
        first_col = [None] * (2*self.nr_qubits)
        for grid_row in range(2*self.nr_qubits):
            #If this qubit (or associated qubit) has a special name:
            if grid_row < self.nr_qubits and self.channel_names[grid_row]:
                txt = f'|{self.channel_names[grid_row]}>'
            elif grid_row >= self.nr_qubits and self.channel_names[grid_row]:
                txt = str(self.channel_names[grid_row])
            else:
                txt = f'|q{grid_row}>' if grid_row < self.nr_qubits else f'b{grid_row-self.nr_qubits}'
            
            ge = GridElement(self.canvas, row=grid_row, col=-1, gate=txt, participant_rows = [grid_row])
            ge.canvas_elem.draw_rect = False
            first_col[grid_row] = ge
        
        #Find out how large each column has to be, but let it be -1 for the first (naming) col
        min_col_widths = [-1] + [ max( self.grid[row][col].get_min_dims()[0] for row in \
             range(2*self.nr_qubits) if col in self.grid[row].keys() ) for col in range(self.max_col) ]
        #Manually set the first column
        min_col_widths[0] = max( ge.get_min_dims()[0] for ge in first_col )
        
        #Specify the width of the columns: add any left-over width evenly
        col_widths = [ int( x + (width-sum(min_col_widths))/nr_cols ) for x in min_col_widths ]
        #Specify the height per row: simply evenly space it, except for the subroutine row
        if extra_row:
            extra_row_size = self.font.metrics('linespace')*2
            row_heights = [int( (height-extra_row_size) /(nr_rows-1) )] * (nr_rows-1) + [extra_row_size]
        else:
            row_heights = [ int(height/nr_rows) ] * nr_rows
        
        #Prepare each GridElement for drawing. This has to be done BEFORE ge.draw()'s are called, because we need
        #to connect adjacent GridElements but cannot do this unless each GridElement has already gotten a bbox.
        for col in range(nr_cols):
            for draw_row in range(nr_rows-extra_row):
                grid_row = to_gridrow[draw_row]
                bbox = {'x': sum(col_widths[:col]), 'y': sum(row_heights[:draw_row]), \
                        'w':col_widths[col], 'h':row_heights[draw_row]}
                if col == 0:
                    first_col[grid_row].set_bbox(bbox)
                    continue
                
                ccol = col-1
                if ccol in self.grid[grid_row].keys():
                    self.grid[grid_row][ccol].set_bbox(bbox)
        
        #Draw the GridElements and the horizontal quantum/classical lines
        for col in range(nr_cols):
            for draw_row in range(nr_rows-extra_row):
                grid_row = to_gridrow[draw_row]
                #Create a bbox for this region
                bbox = {'x': sum(col_widths[:col]), 'y': sum(row_heights[:draw_row]), \
                        'w':col_widths[col], 'h':row_heights[draw_row]}
                if col == 0:
                    ge = first_col[grid_row]
                    ge.draw()
                    continue
                    
                #Now, make a circuit column that is shifted!
                ccol = col-1
                
                #Find the x-coord for the quantum/classical line that is attached to the LEFT GridElement
                #if no such GridElement exists, set it to bbox['x'].
                if ccol == 0:
                    x1 = first_col[grid_row].get_attachments()['right']
                else:
                    x1 = self.grid[grid_row][ccol-1].get_attachments()['right'] if \
                                ccol-1 in self.grid[grid_row].keys() else bbox['x']
                    
                #If this cell actually has a GridElement, then draw it
                ge = None
                if ccol in self.grid[grid_row].keys():
                    ge = self.grid[grid_row][ccol]
                    ge.draw()
                    
                #Find the second x-coord for the quantum/classical line by attaching to the RIGHT GridElement
                #if no such GridElement exists, set it to bbox['x']+bbox['w'].
                x2 = ge.get_attachments()['left'] if ge else bbox['x']+bbox['w']
                
                #Find the middle y coordinate
                y_mid = int( bbox['y'] + bbox['h']/2 )
                
                #Determine whether this should be a quantum (single) wire, or a classical (double) wire.
                if draw_row < self.nr_qubits:
                    self.canvas.create_line(x1,y_mid, x2, y_mid)
                else:
                    self.canvas.create_line(x1,y_mid-2,x2,y_mid-2)
                    self.canvas.create_line(x1,y_mid+2,x2,y_mid+2)
                    
                #If this is the last column, draw the last line if this is a GridElement
                if ccol == nr_cols-2 and ge:
                    x1 = ge.get_attachments()['right']
                    x2 = bbox['x']+bbox['w']
                    if draw_row < self.nr_qubits:
                        self.canvas.create_line(x1,y_mid,x2,y_mid)
                    else:
                        self.canvas.create_line(x1,y_mid-2,x2,y_mid-2)
                        self.canvas.create_line(x1,y_mid+2,x2,y_mid+2)
                    
        #Helper function that draws vertical lines between GridElements.
        def draw_vertical(ge, col, x, classical=False):
            nonlocal row_heights, to_gridrow, extra_row, nr_rows
            
            #Helper function that draws a vertical line between y1 and y2 at x.
            def draw_line(x,y1,y2):
                nonlocal classical
                if classical:
                    self.canvas.create_line(x-2,y1,x-2,y2)
                    self.canvas.create_line(x+2,y1,x+2,y2)
                else:
                    self.canvas.create_line(x,y1,x,y2)
            
            #Determine between which rows we need a wire
            target_rows = ge.participant_rows
            start_grid_row, end_grid_row = min(target_rows),  max(target_rows)
            
            #Find the starting position of the wire: attach it to the bottom of the topmost participant.
            y1 = self.grid[start_grid_row][col].get_attachments()['bottom']
            
            #As we always draw all quantum registers, we can safely start with draw_row = start_grid_row.
            draw_row = start_grid_row
            
            while draw_row < nr_rows-1-extra_row:
                draw_row += 1
                grid_row = to_gridrow[draw_row]

                row_y = sum(row_heights[:draw_row])
                row_h = row_heights[draw_row]
                
                #If this (row,col) contains a GridElement, attach the vertical line to its top.
                if col in self.grid[grid_row].keys():
                    y2 = self.grid[grid_row][col].get_attachments()['top']
                    draw_line(x,y1,y2)
                    y1 = self.grid[grid_row][col].get_attachments()['bottom']
                else:
                    y2 = row_y + row_h
                    draw_line(x,y1,y2)
                    y1 = y2
                    
                if grid_row == end_grid_row:
                    break
                    
            
        #Draw the vertical quantum/classical lines, skip over naming index
        for col in range(1,nr_cols):
            #Only loop over the quantum registers!
            for row in range(self.nr_qubits):
                mid_x = int(sum(col_widths[:col]) + col_widths[col]/2)
                
                #Circuit col is shifted!
                ccol = col-1
                if ccol in self.grid[row].keys():
                    ge = self.grid[row][ccol]
                    #If this is a multi-gate (either measure or multi-qubit)
                    if len(ge.participant_rows) > 1:
                        draw_vertical(ge, ccol, mid_x, classical=\
                                      (ge.gate in ('measure','c-x','c-z') or 'class' in ge.gate) )
                        
        #Draw the subroutines, if any
        if extra_row:
            draw_row = nr_rows-1
            for subroutine in self.subroutines:
                start_col = subroutine['start']+1 #note +1 as the first column has become the naming column!
                end_col = subroutine['end'] #no +1 as this is an inclusive end!
                repeat = subroutine['repeat']
                name = subroutine['name']
                bbox = {'x': sum(col_widths[:start_col]), 'y':sum(row_heights[:draw_row]), \
                       'w': sum(col_widths[start_col:end_col+1]), 'h':row_heights[draw_row]}
                
                y2 = self.draw_subroutine(bbox, name, repeat)
                
                #Additionally, add dashed vertical lines throughout the entire circuit to denote a subroutine.
                x1 = bbox['x']
                x2 = bbox['x']+bbox['w']
                y1 = int(row_heights[0] * 1/4)
                self.canvas.create_line(x1,y1,x1,y2, dash=(5,1), width=2 )
                self.canvas.create_line(x2,y1,x2,y2, dash=(5,1), width=2)
                    
    def draw_subroutine(self, bbox, name, repeat):
        '''Draws a subroutine in the provided bbox'''
        txt = name + '(' + str(repeat) + ')' if repeat > 1 else name
        margin = 3
        size_y = self.font.metrics('linespace')
        size_x = self.font.measure(txt)
        
        leftover_h = bbox['h'] - size_y - margin
        
        text_midx = int(bbox['x'] + bbox['w']/2)
        text_midy = int(bbox['y'] + bbox['h'] - size_y/2 - margin/2)
        arrow_y = int( bbox['y'] + leftover_h/2 )

        self.canvas.create_line(bbox['x'], arrow_y, bbox['x']+bbox['w'], arrow_y, arrow=tk.BOTH, width=2)
        self.canvas.create_text(text_midx, text_midy, text=txt, font=self.font, justify=tk.CENTER )
        
        return arrow_y
        
    def build_font(self):
        '''Builds the font needed to render'''
        for font_dict in self.STD_FONTS:
            try:
                self.font = Font(family=font_dict['family'], size=font_dict['size'])
                if self.font:
                    break
            except Exception as e:
                pass
        else:
            raise ValueError(f'{self} build_font could not produce any font!')
        
    def read(self,data, verbose=False):
        '''Reads the <data> and builds the <self.grid>'''
        if verbose: print('Running renderer')
        
        #We can only read lists/tuples of data, or multi-strings separated by \n statements
        if not isinstance(data,str) or isinstance(data,list) or isinstance(data,tuple):
            raise TypeError('CircuitRender only works with str,list,tuple')
            
        if isinstance(data,str):
            data = data.split('\n')
            
        curr_row = 0
        
        #Let us first look for the amount of qubits, disregard rows previous to that
        if verbose: print('Finding nr of qubits...')
        while True:
            line = data[curr_row]
            #Consider only that part of the line that is not a comment
            if '#' in line:
                line = line[0:line.index('#')]
            
            #If this line contains the 'qubits' statement, this is the row that we are looking for
            if 'qubits' in line:
                break
                
            curr_row += 1
            if curr_row == len(data):
                raise ValueError('CircuitRender did not find "qubits"-line in code')
        if verbose: print(f'Found nr of qubits on line {curr_row+1}: {line}')
            
        if verbose: print('Setting up for line-by-line decoding...')
        #Now, we know curr_row contains the "qubits" mark, let us see how many
        self.nr_qubits = int(data[curr_row].split(' ')[1])
        
        #Keep track of the 'map' possibilities
        self.channel_names = [None for _ in range(2*self.nr_qubits)]
        
        #Initialize the grid for q0...qn and b0...bn
        self.grid = [ {} for _ in range(2*self.nr_qubits) ]
        
        #Initalize the subroutines
        self.subroutines = []
        
        #Keep track of whether we are in a subroutine
        subroutine_name = None
        in_subroutine = False
        subroutine_repeat = -1
        subroutine_start = -1
        
        #Keep track of which column we are in the circuit
        curr_col = 0
        #If we have multiple gates in parallel, freeze the curr_col for the number of gates
        curr_col_parallel = -1
        
        #Keep track of the classical information <angle> as last argument in some gates
        angle = None

        #Flushes the subroutine, meaning that we append the current subroutine to the self.subroutines,
        #and then clear out the in_subroutine flag.
        def flush_subroutine():
            nonlocal in_subroutine, subroutine_start, subroutine_repeat, \
                    subroutine_name, curr_col
            
            if not in_subroutine:
                raise RuntimeError('CircuitRenderer tries to flush_subroutine() whilst in_subroutine=False')
            
            self.subroutines.append( {'start':subroutine_start, 'repeat':subroutine_repeat, \
                                     'end':curr_col, 'name':subroutine_name} )
            
            in_subroutine = False
        
        if verbose: print('Starting line-by-line examination...')

        #Loop over all the data after the 'qubits n' statement. Note that the length of the data can dynamically
        #change, as we INSERT data in the case of a multi-gate line like {h q0 | x q1}, so use len(data) here!
        while curr_row < len(data)-1:
            curr_row += 1
            line = data[curr_row]
            
            if verbose: print(f'Analyzing row {curr_row} : {line}')
            
            #Is this line a white line? Continue
            if len(line.strip()) == 0:
                if verbose: print('White Line! Continuing...')
                continue
                
            #Consider only that part of the line that is not a comment
            if '#' in line:
                line, comment = line[0:line.index('#')] , line[line.index('#'):]
            
                #If the entire line was a comment, UPDATE: comment might also be indented, so we make it line.lstrip()
                if len(line.lstrip()) == 0:
                    if verbose: print('Comment line! Continuing...')
                    continue
                if verbose: print(f'Found a comment on this line! Now only considering part <{line}>')
            
            #Exclude 'display' from the files
            if 'display' in line:
                if verbose: print('This is a <display> line! Continuing...')
                continue
                
            #If this is multiple gates in parallel, which is given by a line like "h q0 | x q1 | toffoli q2,q3,q4"
            if '|' in line:
                if verbose: print('This is a parallel-do line! Splitting up the line...')
                lines = line.split('|')
                first = lines[0]
                last = lines[-1]
                #Remove the tokens '{' and '}' if they are present
                if '{' in first:
                    lines[0] = first[first.index('{')+1:]
                if '}' in last:
                    lines[-1] = last[:last.index('}')]
                    
                #Add this to the queue
                data = data[:curr_row+1] + lines + data[curr_row+1:]
                
                #Continue, but freeze the column for the coming lines!
                curr_col_parallel = len(lines)
                
                #Now, simply continue doing the routine for each statement
                continue
            
            #Split the line into the required elements
            elems = []
            #If the line exists entirely of only one statement, such as 'measure'
            if len(line.split()) == 1:
                elems = [line.strip()]
            else:
                #Remove any starting spaces from the line
                line_s = line.lstrip()
                #split on the first space
                elems.append( line_s[:line_s.index(' ')] )
                #loop over the arguments and parse them correctly
                elems += [arg.strip() for arg in line_s[line_s.index(' ')+1:].split(',') ]
            #The command is case-insensitive
            elems[0] = elems[0].lower()
                    
            if verbose: print(f'Split line into parts: {elems}')
            
            #If this is the start of a subroutine
            if '.' in elems[0]:
                if verbose: print('This is a subroutine call!')
                #If we were still in a subroutine, this is the end of it, and we need to write it
                if in_subroutine:
                    if verbose: print('Flushing the previous subroutine...')
                    flush_subroutine()
                
                in_subroutine = True
                subroutine_start = curr_col
            
                #If this subroutine has to be run multiple times, it is indicated by ".subroutine(nr_of_times)"
                if '(' in line:
                    subroutine_repeat = int( line[ line.index('(')+1:line.index(')') ] )
                    subroutine_name = line[ line.index('.')+1:line.index('(') ].strip()
                else:
                    subroutine_repeat = 1
                    subroutine_name = line[ line.index('.')+1: ].strip()

                #This line contains no more information
                continue
                
            #If this is the end of a subroutine, which we can check because the line is not indented
            if in_subroutine and line[0] != ' ':
                if verbose: print('We were in a subroutine, but this line does not start with a space, so ending routine...')
                flush_subroutine()
                
            #TODO : I have not implemented this, so I'll just skip it
            if 'error_model' in line:
                if verbose: print('This is an error_model line! Skipping...')
                continue
                
            #Check whether this is a valid command
            if elems[0] not in self.POSS_STATEMENTS.keys():
                raise SyntaxWarning(f'CircuitRenderer does not understand command {line}')
        
            #Check whether this has a valid amount of parameters
            if (elems[0] not in self.POSS_STATEMENTS_EXCEPT and self.POSS_STATEMENTS[elems[0]] != len(elems)-1 )\
                or (elems[0] in self.POSS_STATEMENTS_EXCEPT and self.POSS_STATEMENTS[elems[0]] > len(elems)-1):
                raise SyntaxWarning(f'CircuitRenderer: this command has the incorrect amount of parameters: {line}')
            
            #Check whether this is a 'map' statement
            if elems[0] == 'map':
                if verbose: print('This is a mapping! Producing the map...')
                target = elems[1]
                #The target HAS to be either of the form 'q3' or 'b4' for an arbitrary number.
                if 'q' in target:
                    nr = int( target[ target.index('q')+1: ] )
                elif 'b' in target:
                    nr = int( target[ target.index('b')+1: ]) + self.nr_qubits
                else:
                    raise SyntaxWarning(f'CircuitRenderer: cannot map {target} because it is not a qubit or classical bit in line {line}')
                self.channel_names[nr] = elems[2]
                
                #Don't update the column, but if this is parallel, keep track of it
                if curr_col_parallel > 1:
                    if verbose: print(f'This was a parallel operation, still {curr_col_parallel-1} to go!')
                    curr_col_parallel -= 1
                continue
            
            #Now, we know that we have a valid <gate> statement. Let us implement this gate.
            #One exception that does not have extra arguments:
            if elems[0] == 'measure' and len(elems) == 1:
                if verbose: print('Doing a measurement on ALL the qubits...')
                #Set the qubits to 'measure'
                for x in range(self.nr_qubits):
                    ge = GridElement(self.canvas, row=x, col=curr_col, gate='measure',\
                                    participant_rows=[x,x+self.nr_qubits])
                    self.grid[x][curr_col] = ge
                #Set the classical channels to 'measure'
                for x in range(self.nr_qubits,2*self.nr_qubits):
                    ge = GridElement(self.canvas, row=x, col=curr_col, gate='measure',\
                                     participant_rows=[x,x-self.nr_qubits])
                    self.grid[x][curr_col] = ge
            
            #Check if this is a gate with classical info in it
            if elems[0] in ('rx','ry','rz'):
                if verbose: print('This is a gate with an angle! Recording the angle...')
                #It is always an angle, and it is always the last element
                angle = elems.pop()
                
            #Let us find the row indices corresponding to the qubits involved
            row_indices = []
            for elem in elems[1:]:
                if elem in self.channel_names: #this is a user-defined name through 'map'
                    row_indices.append( self.channel_names.index(elem) )
                elif re.search(r'q\d+',elem): #Check if this is of the form qx for some number x:
                    row_indices.append( int( elem[ elem.index('q')+1 : ] ) )
                elif re.search(r'b\d+',elem): #Check if this is of the form bx for some number x:
                    row_indices.append( int( elem[ elem.index('b')+1 : ]) + self.nr_qubits )
                else: 
                    raise SyntaxWarning(f'CircuitRenderer: cant find qubit name: {elem} in line {line}')
            if verbose: print(f'From elements {elems[1:]} we produced the row numbers {row_indices}')        
            
            #Check if this is an ambiguous gate, and check which situation we have
            if elems[0] in ('cx','cz'):
                #This is the classical-quantum situation 'cx b0,b1,q1' for example
                if row_indices[0] >= self.nr_qubits:
                    elems[0] = 'class_'+elems[0]
                    if verbose: print(f'Found classical-qubit gate {elems[0]}')
            
            #Now, we have all participants captured in row_indices
            if verbose: print('Producing the GridElements...')
            for row in row_indices:
                participant_rows = row_indices[:]
                if elems[0] == 'measure':
                    participant_rows.append(row+self.nr_qubits)
                    
                ge = GridElement(self.canvas, row=row, col=curr_col, gate=elems[0],\
                                 participant_rows=participant_rows)
                self.grid[ row ][curr_col] = ge
                
                #If the operation corresponds to a measurement, also set the classical channels
                if elems[0] == 'measure':
                    ge = GridElement(self.canvas, row=row+self.nr_qubits, col=curr_col, gate='measure',\
                                    participant_rows = participant_rows)
                    self.grid[row+self.nr_qubits][curr_col] = ge
            
            if not angle is None:
                ge.angle = angle
                angle = None
            
            #Update the column of the circuit, but only if it wasn't a parallel-gates style!
            if curr_col_parallel <= 1:
                curr_col += 1
            else:
                if verbose: print(f'This was a parallel operation, still {curr_col_parallel-1} to go!')
                curr_col_parallel -= 1
        #if we ended with a subroutine, we still need to flush it
        if in_subroutine:
            flush_subroutine()
            
        if verbose: print('We are done!')
        
        #Set up the maximum nr of columns
        self.max_col = curr_col
        
class GridElement(object):
    '''GridElement keeps track of a Circuit-element in a specific grid location'''
    
    #Changes the script-name of the gate to the display-name of the gate
    GATE_MASKS = {'h':'H', 'x':'X', 'y':'Y', 'z':'Z', 'rx':'Rx', 'ry':'Ry',\
                 'rz':'Rz', 's':'S', 'ph':'S','t':'T', 'tdag':'T^', 'measure':'Meas.', 'prepz':'|0>'}
    #In the case of a multiple-qubit gate, say what kind of circuit we need to draw.
    MULTI_QUBIT_SIGNS = {'cnot':('circ','oplus'), 'cx':('circ','oplus'),\
                         'toffoli':('circ','circ','oplus'),\
                        'swap':('cross','cross'), 'cphase':('circ','circ'),\
                         'cz':('circ','circ'), 'cr':('circ','circ')}
    #In the case of a gate also involving a classical channel
    CLASSICAL_QUBIT_SIGNS = { 'class_cx':('circ','x'),'c-x':('circ','x'),\
                             'class_cz':('circ','z'), 'c-z':('circ','z')}

    def __init__(self, canvas, row=0, col=0, gate=None, participant_rows = None, angle=None):
        self.canvas = canvas
        self.row = row
        self.col = col
        self.participant_rows = participant_rows if participant_rows else [self.row]
        self.angle = angle
        
        self.canvas_elem = None
        if gate:
            self.set_gate(gate)
        
    def set_gate(self,gate):
        self.gate = gate
        #If the gate is a standard one-qubit gate, draw it as a square
        if self.gate in self.GATE_MASKS.keys():
            #Unless this is a measurement gate, and this is the classical part
            if self.gate == 'measure' and self.row == max(self.participant_rows):
                self.canvas_elem = CanvasElem(self.canvas, gate=self.gate, special_node = 'circ')
            else:
                self.canvas_elem = CanvasElem(self.canvas, gate=self.gate, aspect=(1,1) )
        
        #If the gate is a multi-qubit gate, find out which element we are, and pass this along
        elif self.gate in self.MULTI_QUBIT_SIGNS.keys():
            idx = self.participant_rows.index(self.row)
            self.canvas_elem = CanvasElem(self.canvas, gate=self.gate, \
                                          special_node = self.MULTI_QUBIT_SIGNS[self.gate][idx])
        #If the gate is a classical-qubit gate
        elif self.gate in self.CLASSICAL_QUBIT_SIGNS.keys():
            #Simple trick: there's always only one quantum channel involved, and this must be the smallest!
            if self.row == min(self.participant_rows): #we are the quantum channel involved
                gate = self.CLASSICAL_QUBIT_SIGNS[self.gate][-1]
                self.canvas_elem = CanvasElem(self.canvas, gate=gate, aspect=(1,1))
            else:
                node = self.CLASSICAL_QUBIT_SIGNS[self.gate][0]
                self.canvas_elem = CanvasElem(self.canvas, gate=self.gate,\
                                             special_node = node)
        
        else:
            self.canvas_elem = CanvasElem(self.canvas, gate=self.gate)
            
    def set_bbox(self,bbox):
        if not self.canvas_elem:
            raise ValueError(f'{self.__str__()} has no canvas_elem and thus cannot set bbox')
            
        self.canvas_elem.set_bbox(bbox)
        #Automatically also reset the draw coords
        self.set_draw_coords()
        
    def set_draw_coords(self):
        if not self.canvas_elem:
            raise ValueError(f'{self.__str__()} has no canvas_elem and thus cannot set draw coords')
        self.canvas_elem.find_draw_coords()
        
    def draw(self):
        if not self.canvas_elem:
            raise ValueError(f'{self.__str__()} has no canvas_elem and thus cannot draw')
        
        self.canvas_elem.draw()
            
    def get_min_dims(self):
        if not self.canvas_elem:
            raise ValueError(f'{self.__str__()} has no canvas_elem to get min dimensions from')
            
        return (self.canvas_elem.min_w, self.canvas_elem.min_h)
    
    def get_attachments(self):
        if not self.canvas_elem:
            raise ValueError(f'{self.__str__()} has no canvas_elem to get attachments from')
            
        return self.canvas_elem.attachments
        
    def __str__(self):
        return f'G.E.(row={self.row},col={self.col},gate={self.gate},part={self.participant_rows}' +\
                (f'{self.angle})' if not self.angle is None else ')')
    def __repr__(self):
        return self.__str__()

class CanvasElem(object):
    '''CanvasElem keeps track of a canvas element, possibly with text.'''
    
    STD_FONTS = [ {'family':'Bookman Old Style', 'size':14},\
                  {'family':'Century', 'size':14}, \
                  {'family':'Courier', 'size':14}]
    
    #Changes the script-name of the gate to the display-name of the gate
    GATE_MASKS = {'h':'H', 'x':'X', 'y':'Y', 'z':'Z', 'rx':'Rx', 'ry':'Ry',\
                 'rz':'Rz', 's':'S', 'ph':'S','t':'T', 'tdag':'T^', 'measure':'M', 'prepz':'|0>'}
    #All the gates that have a special drawing style
    SPECIAL_GATES = ('cnot', 'cx', 'toffoli', 'swap', 'cphase', 'cz', 'cr','c-x','c-z','class_cx','class_cz')
    SPECIAL_NODES = ('circ','oplus','cross')
    #Determine the radius of the associated nodes of the special gates
    RADII = {'circ':5, 'oplus': 9, 'cross':6 }
    
    #Determine the width of the boxes around the gates
    BORDER_WIDTH = 3
    
    #Determine the margins around the gates.
    MARGINS = (0,0) #(5,5)
    
    def __init__(self, canvas, gate=None, aspect = (-1,-1), bbox=None, font_dict=None,\
                 special_node = None, draw_rect = True):
        self.canvas = canvas
        
        self.aspect = aspect
        self.bbox = bbox

        #Keep track of the actual drawing coordinates
        self.draw_x = -1
        self.draw_y = -1
        self.draw_w = -1
        self.draw_h = -1
        self.text_x = -1
        self.text_y = -1
        
        #Keep track of the min dimensions of the bbox such that the contents can be displayed correctly
        self.min_w = -1
        self.min_h = -1
        
        #Keep track of the attachment points to which other elements can attach themselves.
        self.attachments = {'left':-1, 'right':-1, 'top':-1, 'bottom':-1}
        
        #Keep track of the text within the rectangle
        self.text = None
        #Set the font
        self.font = None
        if font_dict:
            self.font = Font(family=font_dict['family'], size=font_dict['size'])
        else:
            for font_dict in self.STD_FONTS:
                try:
                    self.font = Font(family=font_dict['family'],size=font_dict['size'])
                    if self.font:
                        break
                except Exception as e:
                    pass
            else:
                raise ValueError(f'{self.__str__()} cannot produce any font, none worked!')
        
        #Keep track of the canvas elements
        self.rect_canvas = None
        self.text_canvas = None
        self.special_node = special_node
        self.specials_canvas = []
        
        #Keep track of whether we need to draw the rectangle
        self.draw_rect = draw_rect
        
        #Update the current gate, and the associated text
        self.set_gate(gate)
        
    def find_min_size(self):
        '''Finds the minimum size of the rectangle needed to contain the text'''
        if self.special_node:
            #self.min_w = max(2 * self.RADIUS, self.font.measure('x'), self.font.measure('o'))
            #self.min_h = max(2 * self.RADIUS, self.font.metrics('linespace'))
            self.min_w = self.min_h = 2 * self.RADII[self.special_node]
            
        #If we are an element with actual text inside, compute how large the text is
        elif self.text:
            min_w = self.font.measure(self.text) + self.draw_rect*self.BORDER_WIDTH*2
            min_h = self.font.metrics('linespace') + self.draw_rect*self.BORDER_WIDTH*2
            #Take into account the aspect ratio in self.aspect
            if not -1 in self.aspect:
                #We must have w/h = aspect[0]/aspect[1] => w  = h * aspect[0]/aspect[1]
                #Either stretch w, or stretch h
                if min_h * self.aspect[0]/self.aspect[1] > min_w:
                    self.min_w = int( min_h * self.aspect[0]/self.aspect[1] )
                    self.min_h = int(min_h)
                else:
                    self.min_w = int(min_w)
                    self.min_h = int( min_w * self.aspect[1]/self.aspect[0] )
            else:
                self.min_w = int(min_w)
                self.min_h = int(min_h)
            
            
    def set_bbox(self,bbox):
        self.bbox = bbox
        
    def set_gate(self,gate):
        self.gate = gate
        if self.gate in self.GATE_MASKS.keys():
            self.text = self.GATE_MASKS[self.gate]
        #If the gate is a special gate, suppress the text. Otherwise, set it.
        elif self.gate in self.SPECIAL_GATES:
            self.text = None
        else:
            self.text = self.gate
            
        self.find_min_size()

    def find_draw_coords(self):
        '''Finds the coordinates to draw with, and sets up the attachment points'''
        if self.bbox is None:
            raise ValueError(f'{self.__str__()} cannot find draw coords because bbox is None!')
        
        #Do NOT include margins if we are building a special node
        if self.special_node:
            want_width = self.min_w
            want_height = self.min_h
        else:
            want_width = self.min_w + 2 * self.MARGINS[0]
            want_height = self.min_h + 2 * self.MARGINS[1]

        self.draw_w = want_width if want_width < self.bbox['w'] else self.bbox['w']
        self.draw_h = want_height if want_height < self.bbox['h'] else self.bbox['h']

        self.draw_x = int( self.bbox['x'] + (self.bbox['w'] - self.draw_w)/2 )
        self.draw_y = int( self.bbox['y'] + (self.bbox['h'] - self.draw_h)/2 )

        self.text_x = int( self.draw_x + self.draw_w/2 )
        self.text_y = int( self.draw_y + self.draw_h/2 )

        self.attachments['left'] = self.draw_x
        self.attachments['right'] = self.draw_x + self.draw_w
        self.attachments['top'] = self.draw_y
        self.attachments['bottom'] = self.draw_y + self.draw_h

        
    def draw(self):
        '''Draws the element on the canvas'''
        #First, find the coords at which we should draw.
        self.find_draw_coords()
        
        #If we are a normal node:
        if self.special_node is None:
            #If we should draw a rectangle:
            if self.draw_rect:
                self.rect_canvas = self.canvas.create_rectangle(self.draw_x,self.draw_y,\
                                        self.draw_x+self.draw_w,self.draw_y+self.draw_h,width=self.BORDER_WIDTH)
            
            #If we are a measurement device
            if self.gate == 'measure':
                self.specials_canvas += self.draw_measurement()
            #If we have text:
            elif self.text:
                self.text_canvas = self.canvas.create_text(self.text_x,self.text_y,font=self.font, justify=tk.CENTER,\
                                                          text=self.text)
        
        else: #We are special: we need to draw either a circ, an oplus or a cross
            def node(xy, r, circ=False, fill=False, plus=False, cross=False):
                out = []
                if circ:
                    out.append(self.canvas.create_oval( xy[0]-r, xy[1]-r, xy[0]+r, xy[1]+r, fill='black' if fill else '', width=1.5) )
                if plus:
                    out.append(self.canvas.create_line( xy[0], xy[1]-r, xy[0], xy[1]+r, width=2 ) )
                    out.append(self.canvas.create_line( xy[0]-r, xy[1], xy[0]+r, xy[1], width=2 ) )
                if cross:
                    out.append(self.canvas.create_line( xy[0]-r, xy[1]-r, xy[0]+r, xy[1]+r, width=2.5 ) )
                    out.append(self.canvas.create_line( xy[0]-r, xy[1]+r, xy[0]+r, xy[1]-r, width=2.5 ) )
                return out
            
            mid_x = int( self.bbox['x'] + self.bbox['w']/2 )
            mid_y = int( self.bbox['y'] + self.bbox['h']/2 )
            
            if self.special_node == 'circ':
                self.specials_canvas += node((mid_x,mid_y), self.RADII['circ'], circ=True, fill=True )
            elif self.special_node == 'oplus':
                self.specials_canvas += node((mid_x,mid_y), self.RADII['oplus'], circ=True, plus=True)
            else:
                self.specials_canvas += node((mid_x,mid_y), self.RADII['cross'], cross=True)
                
    def draw_measurement(self):
        '''Draws a measurement device'''
        mid_x = int(self.draw_x + self.draw_w/2)
        mid_y = int(self.draw_y + 3*self.draw_h/5)
        radius = int( (self.draw_w/2) * 7/10 )
        arc = self.canvas.create_arc( mid_x-radius, mid_y-radius, mid_x+radius, mid_y+radius,\
                                     start=0, extent=180, width=2, style=tk.ARC  )
        end_x = int(self.draw_x + self.draw_w * 8.5/10 )
        end_y = int(self.draw_y + self.draw_h * 1.5/10 )
        arrow = self.canvas.create_line(mid_x, mid_y, end_x, end_y, arrow=tk.LAST, width=2 )
        
        return arc, arrow

    def __str__(self):
        return f'R.D. DRAW(x={self.draw_x},y={self.draw_y},w={self.draw_w},h={self.draw_h},text={self.text})'
    
    def __repr__(self):
        return self.__str__()