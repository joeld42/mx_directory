import os, sys, string, math, random
import datetime
import logging
import random

import markdown

import model
import admin

from fpdf import FPDF

def xstr(s):
    return '' if s is None else s

INSTRUCTIONS = """
INSTRUCTIONS: Please verify the data above and mark with a check in column
on left if correct and no edits need to be made. For edits: Strike through
any information you do not want included in the directory and use the space
provided to indicate any corrections or additional contacts.
<br>
The email address listed will automatically be added to the MX Etree and
the PTA Evite.  Write 'NO ETREE' in the space provided if you prefer
not to receive important school information this way.
"""

class MXDirectoryPDF(FPDF):

    def __init__(self,  classSheetMode):
        FPDF.__init__(self)

        self.classSheetMode = classSheetMode

        self.currClass = "None"

        self.colSpc = 5
        if classSheetMode:
            self.numCols = 1
        else:
            self.numCols = 2

        self.currCol = 0

        self.studentIndex = {}
        self.parentIndex = {}
        self.classroomIndex = {}
        self.indexTitle = None

        self.colWidth = self.calcColWidth( self.numCols )

        self.gradeAbbr = { '1' : '1st', '2' : '2nd', '3' : '3rd', '4' : '4th', '5' : '5th'}

        # use this to offset the first page number
        self.page_start = 0


    def calcColWidth(self, numCols):
        return int((self.w - ((self.l_margin+self.r_margin) + (self.colSpc * (numCols-1))) ) / numCols)

    def header(self):
        # Logo
        #self.image('logo_pb.png', 10, 8, 33)
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        #self.cell(20)
        # Title
        if self.indexTitle:
            self.cell(0, 10, self.indexTitle, 'B', 0  )
        else:
            self.cell(0, 10, self.currClass, 'B', 0 )

        # Line break
        self.ln(10)

    # Page footer
    def footer(self):

        if (self.classSheetMode):
            # Position at 2.8 cm from bottom
            yoffs = 28
            self.set_y(-yoffs)
            self.line( 10, self.h - (yoffs+1), self.w-10, self.h-(yoffs+1) )
            # Arial italic 8
            self.set_font('Arial', 'I', 8 )

            # self.cell( 0, 10, 'Instructions: Please verify the data above and mark with a check if correct. Strike through any information ' )
            # self.ln(4)
            # # self.cell( 0, 10, '')
            # # self.ln(4)
            # self.cell( 0, 10, 'you do not want included in the directory. Use the space provided to indicate any corrections or additional contacts.')

            inst = INSTRUCTIONS.strip().split( '\n')
            inst = ' '.join( inst )
            inst = inst.replace( '<br>', '\n\n' )

            self.multi_cell( 0, 2.5, inst )

            # Page number
            #self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
            self.cell(0, 10, 'Page ' + str(self.classPage) , 0, 0, 'C')
        else:
            # Directory Mode, just page number
            self.set_y(-10)
            self.set_font('Arial', 'I', 10 )
            self.cell(0, 10, str(self.page_no() + self.page_start), 0, 0, 'C')


    def startClass(self, classroom ):

        print ("'%s'" % classroom.teacher)

        # Override class to have 3 columns
        if classroom.teacher == 'Patterson, Mary':
            self.numCols = 3
        else:
            self.numCols = 2

        self.colWidth = self.calcColWidth( self.numCols )

        self.currClass = '%s - Grade %s' % (classroom.teacher, classroom.grade)
        self.currClassShort = '%s %s' % (classroom.teacher.split()[0], self.gradeAbbr.get( classroom.grade, classroom.grade ))
        self.add_page()

        classIndexEntry = '%s / %s' % (classroom.teacher, self.gradeAbbr.get( classroom.grade, classroom.grade ))
        self.classroomIndex[ classIndexEntry ] = [ self.page_no() + + self.page_start ]

        self.currCol = 0
        self.topY = self.get_y()
        self.classPage = 1

    def emitStudent(self, stu ):

        startx = self.get_x()
        starty = self.get_y()

        hite = self._doEmitStudent( stu, True )

        # see if it will fit
        pageMargHite = 25
        if not self.classSheetMode:
            pageMargHite = 10

        if (starty + hite) > (self.h - pageMargHite):

            if self.currCol + 1 < self.numCols:
                self.currCol += 1
                self.set_xy( self.l_margin + ((self.colWidth + self.colSpc) * self.currCol), self.topY )
                startx = self.get_x()
                starty = self.get_y()
            else:
                self.currCol = 0
                self.add_page()
                self.topY = self.get_y()
                self.classPage += 1

                startx = self.get_x()
                starty = self.get_y()


        self._doEmitStudent( stu, False )
        if self.classSheetMode:
            self.rect( startx, starty, self.colWidth, hite - 4)
        else:
            hruleY = starty + (hite-1)
            self.rect( startx, hruleY, self.colWidth, 0.25, 'F' )


    def mset_font(self, measure_only, family,style='',size=0):
        if not measure_only:
            self.set_font( family, style, size )

    def mcell(self, measure_only, w,h=0,txt='',border=0,ln=0,align='',fill=0,link=''):
        if not measure_only:
            self.cell( w, h, txt, border,ln, align, fill, link)

        return h

    def _doEmitStudent( self, stu, monly ):

        hite = 0

        # Student name
        stuName = stu.displayName()

        # Add to the index
        stuIndexEntry = stuName + ' / ' + self.currClassShort
        self.studentIndex[stuIndexEntry] = [ self.page_no() ]


        sz = 12
        self.mset_font( monly, 'Times', 'B', sz)
        while (self.get_string_width( stuName ) > self.colWidth ):
            sz -= 1
            self.mset_font( monly, 'Times', 'B', sz)

            if (sz==5):
                break

        hite += self.mcell( monly, self.colWidth, 6, stu.displayName(), 0, 2)

        # Guardians
        fam = stu.family
        if fam:

            # Don't duplicate addresses
            listedAddrs = []
            listedPhones = []
            first = True
            for g in fam.guardians:

                # add to the index
                if g.lastname and g.firstname:
                    gnameIndex = g.lastname + ', ' + g.firstname
                    if not gnameIndex in self.parentIndex:
                        self.parentIndex[gnameIndex] = set()
                    self.parentIndex[gnameIndex].add( self.page_no() )

                if not first:
                    hite += self.mcell( monly, 0, 2, '', 0, 2)

                first = False
                gname = ( xstr(g.firstname) + ' ' + xstr(g.lastname) ).strip()
                if gname:
                    self.mset_font( monly, 'Arial', 'B', 8)
                    hite += self.mcell( monly, self.colWidth, 4, gname, 0, 2)

                self.mset_font( monly, 'Arial', '', 8)

                fields = [ g.email ]

                if g.address and (not g.address in listedAddrs):
                    addr = g.address
                    fields += [ addr.address1, addr.address2, addr.displayCity() ]
                    listedAddrs.append( addr )

                for p in g.phones:
                    if not p in listedPhones:
                        if p.number:
                        #if p.role and p.number:
                            role = p.role
                            # DBG: we want to list all phones as "Phone"
                            role="Phone"
                            fields += [ '%s: %s' % ( role, p.number)]
                            listedPhones.append(p)

                for field in fields:
                    if field:

                        if not monly:
                            sz = 8
                            self.mset_font( monly, 'Arial', '', sz)
                            while (self.get_string_width( field ) > self.colWidth ):
                                sz -= 1
                                self.set_font( 'Arial', '', sz)
                                if (sz==4):
                                    break

                        hite += self.mcell( monly, self.colWidth, 4, field, 8, 2)

        # Bottom space
        if self.classSheetMode:
            hite += self.mcell( monly, 0, max(4, 40-hite), '', 0, 2)
        else:
            hite += self.mcell( monly, 0, 2, '', 0, 2 )

        return hite

    def checkIndexColumn(self, extra ):
        if self.get_y() + extra > self.h - 20:
            self.currCol += 1

            if (self.currCol >= 2):
                self.add_page()
                self.currCol = 0

            self.colx = self.startx + ((self.indexColWidth+self.colSpc) * self.currCol)

            self.set_xy( self.colx, self.starty )

    def genIndex(self, indexTitle, indexItems, showLetters = True ):
        self.indexTitle = indexTitle

        itemsByLetter = {}
        for item in indexItems:
            letter = item[0][0].upper()

            if not letter in itemsByLetter:
                itemsByLetter[letter] = []
            itemsByLetter[letter].append( item )

        usedLetters = list(itemsByLetter.keys())
        usedLetters.sort()

        self.currCol = 0

        self.indexColWidth = self.calcColWidth( 2 )
        self.add_page()

        self.startx = self.get_x()
        self.starty = self.get_y() + 4

        self.colx = self.startx

        if not showLetters:
            self.ln(15)

        for currLetter in usedLetters:

            if showLetters:
                self.checkIndexColumn(10)

                self.set_font( 'Arial', 'B', 10)
                self.cell( self.indexColWidth, 14, currLetter, 0, 2, 'C' )

                self.set_font( 'Arial', '', 8)
            else:
                self.set_font( 'Arial', '', 10)

            items = itemsByLetter[currLetter]
            items.sort()

            for item in items:

                self.checkIndexColumn(0)

                sItem = item[0]

                pages = list(item[1])
                pages.sort()
                sNum = ','.join(map(str,pages))

                #sNum += random.choice( [ '', '', '', ', 3', ', 12, 43, 1', ', 10'])

                wItem = self.get_string_width( sItem )
                wNum = self.get_string_width( sNum )
                spacer = '.'
                wSpace = self.indexColWidth - (wItem + wNum)
                while self.get_string_width( spacer) < wSpace:
                    spacer += '.'
                wSpace = self.get_string_width( spacer)

                self.cell( wItem, 0, sItem, 0, 0 )
                self.cell( self.indexColWidth - wItem, 0, spacer, 0, 0 )
                self.cell( 4, 0, sNum, 0, 2, 'R' )

                if showLetters:
                    self.ln( 3 )
                else:
                    self.ln( 5 )

                self.set_x( self.colx )




        # self.add_page()
        # self.currCol = 0



    def genStudentIndex(self):

        studentIndexItems = self.studentIndex.items()
        self.genIndex( "Student Index by First Name", studentIndexItems )

        parentIndexItems = self.parentIndex.items()
        self.genIndex( "Guardian Index by Last Name", parentIndexItems )

        classroomIndexItems = self.classroomIndex.items()
        #print self.classroomIndex
        self.genIndex( "Classroom Index", classroomIndexItems, False )

def generatePDF( pdf_file, classSheet ):

    pdf = MXDirectoryPDF(  classSheet )
    pdf.alias_nb_pages()

    pdf.set_auto_page_break( False, 0.0 )

    dbgRoomCount = 0
    sortKeyForGrade = { 'TK' : -1, 'K' : 0, 'KG' : 0,  'X' :99 }
    rooms = list(model.Classroom.query.all())


    rooms.sort( key=lambda x: ( int(sortKeyForGrade.get( x.grade, x.grade )), x.teacher) )

    for room in rooms:

        # Special grade for "Unassigned" students
        if room.grade=='X':
            continue

        # Skip empty teachers
        stus = list(room.students)
        if len(stus)==0:
            continue

        pdf.startClass( room )



        stus.sort( key=lambda x: x.displayName() )
        #rooms.sort( key=lambda x: ( sortKeyForGrade.get( x.grade, "Z"+x.grade ), x.teacher) )

        for stu in stus:
            pdf.emitStudent( stu)

        # DBG - stop early for faster testing
        dbgRoomCount += 1
        #if (dbgRoomCount > 4):
        #    break

    if not classSheet:
        pdf.genStudentIndex()

    pdf.output( pdf_file, 'F')

def generatePDFClassSheet( pdf_file ):
    generatePDF( pdf_file, True )

def generatePDFDirectory( pdf_file ):
    generatePDF( pdf_file, False )