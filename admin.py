#!/bin/env python
# -*- coding: utf-8 -*-

import os, sys, string
import random

from flask import request, session, redirect, url_for, Markup, Response, abort, redirect

from flask.ext.admin import Admin, BaseView, expose
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.model.template import macro

import flask_uploads

import outpdf


from wtforms.fields import SelectField

#from mxafs.model import User, Student, Instructor, CourseInfo, Course, CourseRequest, Payment, Classroom
from model import Family, Address, Phone, Guardian, Student, Classroom, VerifyAddr
from model import db

from bulk_import import importFamilyTSV, importStudentTSV, importStudentAndGuardianTSV, importStudentAndGuardianTSV2017

import model

from flask.ext.admin import Admin, expose, AdminIndexView

from sqlalchemy import or_, and_, func

import markdown
import datetime

tsvUploadSet = flask_uploads.UploadSet( 'tsv', ['tsv','csv'] )

SECRET_ADMIN_TOKEN = 'Y5<84jM>v$:[sU}'

def checkAuth():
    return session.get('admin_auth', None) == SECRET_ADMIN_TOKEN

class MXDirectoryModelView(ModelView):
    page_size = 100

    def is_accessible(self):
        return checkAuth()

class HomeView(AdminIndexView):

    @expose("/")
    def index(self):

        if not checkAuth():
            return self.render('admin/login.html')
        else:
            return self.render('admin/index.html')

    @expose("/admlogin", methods=['POST'])
    def admlogin(self):

        if request.form['password'] == self.adminPass:
            session['admin_auth'] = SECRET_ADMIN_TOKEN
        else:
            session['admin_auth'] = None

        return redirect(url_for('.index'))

    @expose("/admlogout" )
    def admlogout(self):
        session['admin_auth'] = None

        return redirect(url_for('.index'))

    @expose("/import_fam", methods=['POST'])
    def import_fam(self):

        message = "No family data uploaded..."

        if request.method == 'POST' and 'tsv' in request.files:
            filename = tsvUploadSet.save( request.files['tsv'])
            message = importFamilyTSV( tsvUploadSet.path(filename) )

        return "Imported families data...<br>" + message

    @expose("/import_stu_addronly", methods=['POST'])
    def import_stu_addronly(self):

        message = "No student data uploaded..."

        if request.method == 'POST' and 'tsv' in request.files:
            filename = tsvUploadSet.save( request.files['tsv'])
            message = importStudentTSV( tsvUploadSet.path(filename) )

        return "Imported Student data...<br>" + message

    @expose("/import_stu", methods=['POST'])
    def import_stu(self):

        message = "No student data uploaded..."

        if request.method == 'POST' and 'tsv' in request.files:
            filename = tsvUploadSet.save( request.files['tsv'])
            message = importStudentAndGuardianTSV( tsvUploadSet.path(filename) )

        return "Imported Student data...<br>" + message

    @expose("/import_stu2017", methods=['POST'])
    def import_stu2017(self):

        message = "No student data uploaded..."

        if request.method == 'POST' and 'tsv' in request.files:
            filename = tsvUploadSet.save( request.files['tsv'])
            message = importStudentAndGuardianTSV2017( tsvUploadSet.path(filename) )

        return "Imported Student data...<br>" + message

    def gatherEmailList(self):
        emails = []
        unassigned = Classroom.query.filter( Classroom.teacher == 'Unassigned')[0]
        for stu in Student.query.filter( Student.classroom != unassigned ):
            if stu.classroom is None:
                print "No class assigned ", stu.firstname, stu.lastname
                continue

            if stu.family and stu.family.guardians:
                for guardian in stu.family.guardians:
                    if guardian.email:
                        stuname = "%s %s" % (stu.firstname, stu.lastname)
                        teacher = stu.classroom.teacher
                        grade = stu.classroom.grade
                        email = "%s %s <%s>" % (guardian.firstname, guardian.lastname, string.strip(guardian.email))
                        emails.append( (stuname, teacher, grade, email) )

        return emails

    @expose("/report_email_list")
    def reportEmailList(self):
        emails = self.gatherEmailList()

        justEmails = set()
        for info in emails:
            justEmails.add( info[-1])

        justEmails = list(justEmails)
        justEmails.sort()
        rawEmailList = '\n'.join( justEmails )
        return Response(rawEmailList, mimetype='text/plain')

    @expose("/report_email_list_tsv")
    def reportEmailListTsv(self):
        emails =[ ( "Student", "Teacher", "Grade", "Parent Email") ] + self.gatherEmailList()

        rawEmailList = []
        for entry in emails:
            rawEmailList.append( '\t'.join( entry ))

        rawEmailList = '\n'.join( rawEmailList )
        return Response(rawEmailList, mimetype='text/plain')


    @expose("/gen_dir" )
    def genDirectory(self):

        outpdf.generatePDFDirectory( os.path.join( self.pdfPath, 'mx_directory.pdf' ))
        return 'Gen dir'

    @expose("/gen_class" )
    def genClassList(self):
        outpdf.generatePDFClassSheet( os.path.join( self.pdfPath, 'mx_dir_classsheets.pdf' ))

        return 'Gen class'

    @expose("/gen_email_list")
    def genEmailList(self):

        emails = {}

        for fam in Family.query.all():

            hasStuInClassroom = False
            for stu in fam.students:
                if stu.classroom:
                   hasStuInClassroom = True
                   break

            if not hasStuInClassroom:
                continue

            # get emails for all guardians
            count = 0
            for guardian in fam.guardians:

                email = guardian.email
                if email and not emails.has_key( email ):
                    emails[email] = (count, '%s %s &lt%s&gt' % (guardian.firstname, guardian.lastname, email))

                count += 1

        all_emails = list(emails.values())
        all_emails.sort()
        result = ""
        curr_index = -1

        for e in all_emails:
            ndx, email = e
            if ndx != curr_index:
                result += ("<h2>Contact %d</h2>" % (ndx+1))
                curr_index = ndx

            result += email + "<br>"



        return result

        #for student in Student.query.all():
        #    pass

    # --- Routines to handle verify addrs
    @expose('/create_addr/<int:ver_id>')
    def createAddrFromVerify( self, ver_id ):

        print "ver_id is ", ver_id

        verifyAddr = VerifyAddr.query.get( ver_id )
        if not verifyAddr:
            return "Didn't find VerifyAddr for id "+ver_id

        student = verifyAddr.student

        if not student.family:
            family = Family()
            student.family = family
            db.session.add( family )
        else:
            family = student.family

        parent = Guardian()
        parent.family = family

        addr = Address()
        addr.address1 = verifyAddr.matchAddr
        addr.city = model.cityFromZip( None, verifyAddr.zipcode )
        db.session.add( addr )

        parent.address = addr

        student.verifyAddr = None

        db.session.add( parent )
        db.session.commit()

        db.session.delete( verifyAddr )
        db.session.commit()

        return redirect( url_for('guardian.edit_view', id=parent.id ))

    def assignFromVerify( self, ver_id, addr_id, do_update ):

        verifyAddr = VerifyAddr.query.get( ver_id )
        if not verifyAddr:
            return "Didn't find VerifyAddr for id "+ver_id

        addr = Address.query.get( addr_id )
        if not addr:
            return "Didn't find Address for id "+addr_id

        parent = addr.guardians[0]
        fam = parent.family

        verifyAddr.student.family = fam
        db.session.commit()

        return redirect( url_for('verifyaddr'))


    @expose('/verify/<int:ver_id>')
    def verify( self, ver_id ):

        verifyAddr = VerifyAddr.query.get( ver_id )
        if not verifyAddr:
            return "Didn't find VerifyAddr for id "+ver_id

        # Verify address is correct, just remove the
        # VerifyAddr row
        db.session.delete( verifyAddr )
        db.session.commit()

        return redirect( url_for('verifyaddr.index_view'))


    @expose('/assign_addr/<int:ver_id>')
    def assignAddrFromVerify( self, ver_id, addr_id=None ):

        addr_id = request.args.get('addr_id', '')
        if not addr_id:
            return "Missing address id"

        return self.assignFromVerify( ver_id, addr_id, False )

    @expose('/update_addr/<int:ver_id>')
    def updateAddrFromVerify( self, ver_id ):

        addr_id = request.args.get('addr_id', '')
        if not addr_id:
            return "Missing address id"

        return self.assignFromVerify( ver_id, addr_id, True )

    @expose('/duplicate_guardian/<int:guardian_id>')
    def duplicateGuardian(self, guardian_id ):

        if not guardian_id:
            return "Missing guardian id"

        g = Guardian.query.get( guardian_id )
        dupe_guardian = g.duplicate()

        return redirect( url_for('guardian.edit_view', id=dupe_guardian.id) )

    @expose('/guardian_add_address/<int:guardian_id>')
    def quickAddAddress(self, guardian_id ):

        if not guardian_id:
            return "Missing guardian id"

        g = Guardian.query.get( guardian_id )

        addr = Address()

        db.session.add( addr )
        g.address = addr

        db.session.commit()

        return redirect( url_for('address.edit_view', id=addr.id) )

    @expose('/guardian_add_phone/<int:guardian_id>')
    def quickAddPhone(self, guardian_id ):

        if not guardian_id:
            return "Missing guardian id"

        g = Guardian.query.get( guardian_id )
        ph = Phone()
        ph.role = 'Phone'
        ph.number= '(555) 555-5555'
        ph.guardian = g

        db.session.add( ph )
        db.session.commit()

        return redirect( url_for('phone.edit_view', id=ph.id) )


class StudentModelView(MXDirectoryModelView):
    edit_template = 'admin/student_edit.html'

class VerifyAddrModelView(MXDirectoryModelView):
    list_template = 'admin/verify_list.html'
    column_formatters = dict( student=macro('verify_student'))

class ClassroomModelView(MXDirectoryModelView):
    #list_template = 'admin/classroom_list.html'
    edit_template = 'admin/classroom_edit.html'

class GuardianModelView(MXDirectoryModelView):
    edit_template = 'admin/guardian_edit.html'

class FamilyModelView(MXDirectoryModelView):
    page_size = 50
    list_template = 'admin/family_list.html'
    column_list = ('family', 'matchAddr', 'guardians', 'students' )
    column_formatters = dict( family=macro('m_fam_title'),
                              guardians=macro('m_fam_guardians'),
                              students=macro('m_fam_students') )




# Admin interface
def init_admin(app):

    flask_uploads.configure_uploads( app, tsvUploadSet )

    # admin = Admin(app)
    adminHome = HomeView(name='Home')
    admin = Admin(app, "directory.mxpta.org", index_view=adminHome )
                  #, template_mode='bootstrap3' )
    adminHome.pdfPath = app.config['PDF_PATH']
    adminHome.adminPass = app.config['ADMIN_PASSWORD']

    admin.add_view( FamilyModelView( Family, db.session, category='Directory' ))
    admin.add_view( MXDirectoryModelView( Address, db.session, category='Directory' ))
    admin.add_view( MXDirectoryModelView( Phone, db.session, category='Directory' ))

    admin.add_view( GuardianModelView( Guardian, db.session, category='Directory' ))
    admin.add_view( StudentModelView( Student, db.session, category='Directory' ))
    #admin.add_view( MXDirectoryModelView( Student, db.session, category='Directory' ))
    admin.add_view( ClassroomModelView( Classroom, db.session, category='Directory' ))

    admin.add_view( VerifyAddrModelView( VerifyAddr, db.session, category='Verify' ))