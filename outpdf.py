import os, sys, string, math, random
import datetime
import logging

import markdown

import model
import admin

from fpdf import FPDF

class MXDirectoryPDF(FPDF):

    def __init__(self,  classSheetMode):
        FPDF.__init__(self)

        self.classSheetMode = classSheetMode

        self.currClass = "None"

        self.colSpc = 5
        if classSheetMode:
            self.numCols = 1
        else:
            self.numCols = 4

        self.currCol = 0


        self.colWidth = int((self.w - ((self.l_margin+self.r_margin) + (self.colSpc * (self.numCols-1))) ) / self.numCols)

    def header(self):
        # Logo
        #self.image('logo_pb.png', 10, 8, 33)
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        #self.cell(20)
        # Title
        self.cell(0, 10, self.currClass, 1, 0, 'C')
        # Line break
        self.ln(20)

    # Page footer
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.line( 10, self.h - 15, self.w-10, self.h-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8 )
        self.cell( 0, 10, 'Instructions: Please verify the data above and mark with a check if correct. Strike through any information ' )
        self.ln(4)
        # self.cell( 0, 10, '')
        # self.ln(4)
        self.cell( 0, 10, 'you do not want included in the directory. Use the space provided to indicate any corrections or additional contacts.')

        # Page number
        #self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
        self.cell(0, 10, 'Page ' + str(self.classPage) , 0, 0, 'C')

    def startClass(self, classroom ):
        self.currClass = '%s -- Grade %s' % (classroom.teacher, classroom.grade)
        self.add_page()

        self.currCol = 0
        self.topY = self.get_y()
        self.classPage = 1

    def emitStudent(self, stu ):

        startx = self.get_x()
        starty = self.get_y()

        hite = self._doEmitStudent( stu, True )

        # see if it will fit
        if (starty + hite) > (self.h - 20):

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
        self.rect( startx, starty, self.colWidth, hite - 4)


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
        self.mset_font( monly, 'Arial', 'B', 10)
        hite += self.mcell( monly, self.colWidth, 6, stu.displayName(), 0, 2)

        # Guardians
        fam = stu.family
        if fam:

            # Don't duplicate addresses
            listedAddrs = []
            listedPhones = []
            first = True
            for g in fam.guardians:

                if not first:
                    hite += self.mcell( monly, 0, 2, '', 0, 2)

                first = False
                gname = string.strip(g.displayName())
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
                        fields += [ '%s: %s' % ( p.role, p.number)]
                        listedPhones.append(p)

                for field in fields:
                    if field:
                        hite += self.mcell( monly, self.colWidth, 4, field, 0, 2)

        # Bottom space
        hite += self.mcell( monly, 0, max(4, 40-hite), '', 0, 2)



        return hite

def generatePDF( pdf_file, classSheet ):

    pdf = MXDirectoryPDF(  classSheet )
    pdf.alias_nb_pages()

    pdf.set_auto_page_break( False, 0.0 )

    for room in model.Classroom.query.all():

        pdf.startClass( room )
        for stu in room.students:
            pdf.emitStudent( stu)

    pdf.output( pdf_file, 'F')

def generatePDFClassSheet( pdf_file ):
    generatePDF( pdf_file, True )

def generatePDFDirectory( pdf_file ):
    generatePDF( pdf_file, False )