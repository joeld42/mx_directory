#!/bin/env python
# -*- coding: utf-8 -*-

import os, sys, string
import random
import codecs


from flask_sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy.orm import backref, relationship

from sqlalchemy import or_, and_
from sqlalchemy import func

import model
from model import Family, Address, Phone, Guardian, Student, Classroom, VerifyAddr
from model import db

# Use this to override names for different names or dual classes
class ColumnName:
    studentID = "student id"
    teacher = "teacher"
    gradelevel = "grade"
    firstname = "first name"
    lastname = "last name"
    address = "street"
    zipcode = "zip"
    contact_firstname = "contacts_firstname"
    contact_lastname = "contacts_lastname"

    contact_address = "contacts_addressline1"
    contact_city = "contacts_city"
    contact_state = "contacts_state"
    contact_zip = "contacts_zip"
    contact_email =  "contacts_email"

    contact_homephone = "contacts_homephone"
    contact_workphone ="contacts_workphone"
    contact_cellphone ="contacts_cellphone"


# All lowercase even if the remapped names are mixed case
TSV_CNAME_MAPPING = {
    "student_studentnumber" : ColumnName.studentID,
    "student_firstname" : ColumnName.firstname,
    "student_lastname" : ColumnName.lastname,
    "student_homeroomteacher" : ColumnName.teacher,
    #"coursesection_coursename" : "",
    "student_grade" : ColumnName.gradelevel,
    "coursesection_teacherfullname" : ColumnName.teacher,

    "address_guardianfirstname" : ColumnName.contact_firstname,
    "address_guardianlastname" : ColumnName.contact_lastname,
    "address_addressline1" : ColumnName.contact_address,
    "address_city" : ColumnName.contact_city,
    "address_state" : ColumnName.contact_state,
    "address_zip" : ColumnName.contact_zip,    
    # "contacts_firstname" : "",
    # "contacts_lastname" : "",
    # "contacts_addressline1" : "",
    # "contacts_city" : "",
    # "contacts_state" : "",
    # "contacts_zip" : "",
    # "contacts_homephone" : "",
    # "contacts_workphone" : "",
    # "contacts_cellphone" : "",

}

TEACHER_NAME_FIX = {

    'Inthedatafile Name' : 'Name, Inthedatafile',
    #
    # 'Attilah Reese': 'Rainey, Attilah',
    # 'Annastazia Manekin-Hrdy' : 'Cobeen, Richard; Manekin-Hrdy, Zia',
    # 'Richard Cobeen' : 'Cobeen, Richard; Manekin-Hrdy, Zia',
    #
    # 'Jila Abdolhosseini' : 'Beers, Julia; Abdolhosseini, Jila',
    # 'Julia Beers' : 'Beers, Julia; Abdolhosseini, Jila',
    #
    #'Dang, Thuy-Mi' : 'Hunter, Thuy-Mi',
    'Reese, Attilah' : 'Rainey, Attilah',
    'McDaniels, Lachelle' : 'McDaniels, LaChelle',

    # Rewrite co-teachers as combined names
    # 'Abdolhosseini, Jila' : 'Abdolhosseini, Jila and Arroyo, Jessica',
    # 'Arroyo Solis, Jessica' : 'Abdolhosseini, Jila and Arroyo, Jessica',

    # TK Classes not assigned yet
    'Dang, Thuy-Mi' : 'TK Combined',
    'Cottle, Amy' : 'TK Combined',
    'Gill, May Lynne' : 'TK Combined',

    # 'Fletcher, Michele': 'Fletcher, Michele and Allman, Cynthia',
    # 'Allman, Cynthia': 'Fletcher, Michele and Allman, Cynthia',

    'Cobeen, Richard' : 'Cobeen, Richard and Middleton Fraser, Suzanne',
    'Middleton Fraser, Suzanne' : 'Cobeen, Richard and Middleton Fraser, Suzanne',

}

def importFamilyTSV( filename ):

    # TMP : reset db
    #db.drop_all()
    #db.create_all()

    countAddr = 0
    countParents = 0

    colNum = {}
    totalCols = 0

    firstLine = True
    for line in codecs.open( filename, 'r', 'utf-8' ):

        # DBG
        #if countParents > 5:
        #    break

        lsplit = string.split( string.strip(line), '\t' )

        if (firstLine):
            totalCols = len(lsplit)
            for cndx in range(len(lsplit)):
                cname = lsplit[cndx]
                colNum[cname] = cndx

            firstLine = False

        else:
            # Replace nulls with ""
            lsplit2 = []
            for item in lsplit:
                if item=='NULL':
                    item=''

                lsplit2.append(item)
            lsplit = lsplit2

            # Pad out the row
            lsplit += [''] * (totalCols - len(lsplit))

            street_from_tsv = model.normalizeAddress( lsplit[colNum['street_from_tsv']] )
            zip_from_tsv = lsplit[colNum['zip_from_tsv']]

            if not street_from_tsv:
                print( "MISSING MATCHADDR", line )
                continue

            family = Family()
            family.matchAddr = street_from_tsv

            print ( "---- Family ", family )

            countAddr += 1
            print ( "***", street_from_tsv )

            # Use the street_from_tsv as a base address
            baseAddr = Address()
            baseAddr.address1 = street_from_tsv
            baseAddr.zipcode = zip_from_tsv
            baseAddr.city = model.cityFromZip( None, zip_from_tsv)
            #db.session.add( baseAddr )
            #db.session.commit()
            print ("ADDING BASEADDR", baseAddr, baseAddr.address1 )

            defaultAddr = None

            # Now check for up to 4 parent/guardians

            numGuardians = 0
            for i in range(1,5):
                prefix = "p%d_" % i
                firstname = string.strip( lsplit[ colNum[ prefix + "first_name" ]] )
                lastname = string.strip(lsplit[ colNum[ prefix + "last_name" ]] )
                street = string.strip(lsplit[ colNum[ prefix + "street" ]] )
                city = string.strip(lsplit[ colNum[ prefix + "city" ]] )
                zipcode = string.strip(lsplit[ colNum[ prefix + "zip" ]] )
                homephone = string.strip(lsplit[ colNum[ prefix + "home_phone" ]] )
                cellphone = string.strip(lsplit[ colNum[ prefix + "cell_phone" ]] )
                workphone = string.strip(lsplit[ colNum[ prefix + "work_phone" ]] )
                email = string.strip(lsplit[ colNum[ prefix + "email" ]] )

                city = model.cityFromZip( city, zipcode )

                # Any identifier, create a guardian
                if firstname or lastname or email:
                    parent = Guardian()
                    parent.firstname = firstname
                    parent.lastname = lastname
                    parent.email = email
                    parent.family = family

                    countParents += 1

                    print ( "Import parent ", i, firstname, lastname )

                    # Add phones
                    for role, phonenum in [('Home', homephone), ('Work', workphone), ('Cell', cellphone)]:
                        if phonenum:
                            phone = Phone()
                            phone.number = phonenum
                            phone.role = role
                            phone.guardian = parent

                    if street or city or zipcode:

                        # Have address data for this parent, does it
                        # match the base?
                        street = model.normalizeAddress(street)
                        if (street == baseAddr.address1) and (zipcode == baseAddr.zipcode):
                            print ( "GUARDIAN USES BASE ADDR", baseAddr )
                            parent.address = baseAddr
                        else:
                            addr = Address()
                            addr.address1 = street
                            addr.city = city
                            addr.zipcode = zipcode

                            parent.address = addr
                            db.session.add( addr )
                            print ( "ADDING GUARDIAN ADDR", addr )

                        if not defaultAddr:
                            defaultAddr = parent.address
                    else:
                        print ("NO ADDR USING DEFAULT" )
                        if defaultAddr:
                            parent.address = defaultAddr
                        else:
                            parent.address = baseAddr

                    db.session.add( parent )
                    numGuardians += 1

            # If no names were listed, create an empty guardian
            # for this address
            if (numGuardians==0):

                print ("NO GUARDIANS ADDING EMPTY", baseAddr )

                parent = Guardian()
                parent.address = baseAddr
                parent.firstname = ''
                parent.lastname = ''
                parent.email = ''
                parent.family = family
                db.session.add(parent)

                countParents += 1

    db.session.commit()

    return "Added %d Families (%d total parent/guardians)" % (countAddr, countParents )



def importStudentTSV( filename ):

    # Delete all of the current students
    Student.query.delete()

    # Delete all the current verify reqs
    VerifyAddr.query.delete()

    db.session.commit()

    stuCount = 0

    colNum = {}
    totalCols = 0

    needVerify = 0

    firstLine = True
    for line in codecs.open( filename, 'r', 'utf-8' ):
        lsplit = string.split( string.strip(line), '\t' )


        # if stuCount == 5:
        #     break;

        if (firstLine):
            print ( lsplit )
            totalCols = len(lsplit)
            for cndx in range(len(lsplit)):
                cname = lsplit[cndx]
                colNum[cname] = cndx

            firstLine = False
        else:
            # Replace nulls with ""
            lsplit2 = []
            for item in lsplit:
                if item=='NULL':
                    item=''

                lsplit2.append(item)
            lsplit = lsplit2

            # Pad out the row
            lsplit += [''] * (totalCols - len(lsplit))

            firstname = lsplit[ colNum[ ColumnName.firstname ] ]
            lastname = lsplit[ colNum[ ColumnName.lastname ]]
            matchAddr = lsplit[ colNum[ColumnName.address ]]
            zipcode = lsplit[ colNum[ ColumnName.zipcode ]]
            grade = lsplit[ colNum[ ColumnName.gradelevel ]]
            teacher = lsplit[ colNum[ ColumnName.teacher ]]

            student = Student()
            student.firstname = firstname
            student.lastname = lastname
            student.zipcode = zipcode

            matchAddr = model.normalizeAddress(matchAddr)

            print ( "targetAddr is ",matchAddr, zipcode )

            # Query any address from their matchAddr
            family = None
            address = Address.query.filter( and_( (Address.address1==matchAddr),
                                                	(Address.zipcode==zipcode)) ).first()

            if not address:
                print ( "No exact match, trying without zip" )
                # didn't find an exact match, first without the zipcode
                address = Address.query.filter( Address.address1==matchAddr).first()

                if address:
                     # Fix the zip code if it's missing
                     if not address.zipcode:
                         print ( "fixing zip" )
                         address.zipcode = student.zipcode
                         db.session.commit()
                     else:
                         print ( "Mismatched zip codes:", matchAddr, address.zipcode, student.zipcode, "for student", firstname, lastname )


            if address:

                for g in address.guardians:
                    if g.family:
                        family = g.family
                        break

                if not family:
                    print ( "Didn't find guardian for address", address )

            else:

                # Didn't find address, flag for hand-verification
                verify = VerifyAddr()
                verify.matchAddr = matchAddr
                verify.zipcode = zipcode
                verify.student = student
                db.session.add( verify )

                needVerify += 1



            if family:
                student.family = family

            # query for their classroom
            room = Classroom.query.filter( and_((Classroom.teacher==teacher),
                                                     (Classroom.grade==grade))).first()
            if not room:
                room = Classroom()
                room.teacher = teacher
                room.grade = grade

                db.session.add( room )

            student.classroom = room

            db.session.add(student)
            stuCount += 1

    db.session.commit()
    return "Imported %d students (%d addresses need verification)..." % (stuCount, needVerify)

def splitName( fullname ):
    nsplit = string.split( fullname, ' ' )
    return nsplit[0], ' '.join(nsplit[1:])

def fixPhone( phone ):
    if phone:
        return "%s-%s-%s" % (phone[0:3], phone[3:6], phone[6:])
    else:
        return phone

def addGuardian( family, firstName, lastName, email, baseAddr, phones ):

    parent = Guardian()
    parent.firstname = firstName
    parent.lastname = lastName
    parent.email = email
    parent.address = baseAddr

    parent.family = family
    db.session.add(parent)

    for phoneKey, phoneNum in phones:
        phone = Phone()
        phone.number = phoneNum
        phone.guardian = parent
        phone.role = phoneKey
        db.session.add(phone)

MULTI_G = set()
MISSING_G = set()
def findOrCreateGuardians( stuInfo ):
    #print "STUINFO: ", stuInfo
    #fullname1  = stuInfo["primary contact name (first last)"]
    #firstName1, lastName1 = splitName( fullname1 )
    firstName1 = stuInfo[ ColumnName.contact_firstname ]
    lastName1 = stuInfo[ ColumnName.contact_lastname ]
    address = stuInfo[ ColumnName.contact_address]
    city = stuInfo[ ColumnName.contact_city ]
    zipcode = stuInfo[ ColumnName.contact_zip ]


    # print "DBG addComb ", addressComb
    # print "DBG address ", address
    # print "DBG city ", city
    # print "DBG zipcode", zipcode

    # phone1 = ""
    # if stuInfo.has_key("primary contact phone number"):
    #     phone1 = fixPhone( stuInfo["primary contact phone number"] )
    allPhones = []

    for role, phoneCol in [ ('Work', ColumnName.contact_workphone),
                            ('Home', ColumnName.contact_homephone),
                            ('Cell', ColumnName.contact_cellphone) ]:

        phone = stuInfo.get( phoneCol, "" )
        if phone:
            allPhones.append( ( role, phone ))

    email1= stuInfo[ ColumnName.contact_email ]
    if email1=='':
        # dummy email so it won't match anything
        searchEmail1 = "No EMail!!"
    else:
        searchEmail1 = email1

    #fullname2 = stuInfo["contact name (first last)"]
    #firstName2, lastName2 = splitName( fullname2 )
    #email2 = stuInfo["contact email address"]
    #searchEmail2 = email2
    #if email2=='':
    #    searchEmail2 = "No EMail!!"


    guardian1 = Guardian.query.filter( or_( and_( Guardian.firstname==firstName1,
                                                  Guardian.lastname==lastName1 ),
                                                  Guardian.email==searchEmail1 ) )
    guardian1 = list( guardian1 )
    if (len(guardian1)>1):
        print (">>>> MULTIPLE GUARDIAN ", firstName1, lastName1, email1, len(guardian1) )
        for gg in guardian1:
            print (gg.id, gg.displayName(), gg.email)

    # Found a guardian, return the fam
    if len(guardian1)>0:
        return guardian1[0].family

    # didn't find guardian1, let's try guardian2
    #guardian2 = list(Guardian.query.filter( or_( and_( Guardian.firstname==firstName2,
    #                                          Guardian.lastname==lastName2 ),
    #                                          Guardian.email==searchEmail2 ) ))

    #if (len(guardian2)>1):
    #    print ">>>> MULTIPLE GUARDIAN2 ", fullname2, email2, len(guardian2)
    #    for gg in guardian2:
    #        print gg.id, gg.displayName(), gg.email

    # Found a guardian, return the fam
    #if len(guardian2)>0:
    #    return guardian2[0].family

    # HERE: Create a new family
    #MISSING_G.add( grade + " " + firstName+" "+lastName )

    baseAddr = Address()
    baseAddr.address1 = address
    baseAddr.zipcode = zipcode
    baseAddr.city = city
    db.session.add(baseAddr)

    family = Family()
    family.matchAddr = address
    db.session.add(family)

    #def addGuardian( family, firstName, lastName, email, baseAddr, homePhone ):
    addGuardian( family, firstName1, lastName1, email1, baseAddr, allPhones )

    #if (firstName2 and lastName2):
    #    addGuardian( family, firstName2, lastName2, email2, baseAddr, phone1 )

    return family


def findOrCreateTeacherForStudent( stuInfo ):

    teacherName = fixTeacherName( stuInfo[ ColumnName.teacher ] )

    teacher = list(Classroom.query.filter( Classroom.teacher == teacherName ))
    if len(teacher)==0:
        print ( "COULD NOT FIND TEACHER '%s' (%s)" % ( stuInfo[ ColumnName.teacher ], teacherName ) )

        # Sanitize grade level (e.g. 01 - 1)
        gradeLevel = stuInfo[ColumnName.gradelevel]
        try:
            gradeLevel = int(gradeLevel)
        except ValueError:
            pass

        newClass = Classroom( teacher = teacherName, grade = gradeLevel )

        db.session.add( newClass )
        db.session.commit()

        teacher = newClass

    else:
        teacher = teacher[0]

    return teacher

def createStudent( stuInfo ):

    firstName = stuInfo[ColumnName.firstname]
    lastName = stuInfo [ColumnName.lastname]

    # teacherName = fixTeacherName( stuInfo["teacher"] )
    # teacher = list(Classroom.query.filter( Classroom.teacher == teacherName ))
    # if len(teacher)==0:
    #     print "COULD NOT FIND TEACHER '%s' (%s)" % ( stuInfo["teacher"], teacherName )
    #
    #     newClass = Classroom( teacher = teacherName )
    #     db.session.add( newClass )
    #
    #     teacher = newClass
    #
    # else:
    #     teacher = teacher[0]
    teacher = findOrCreateTeacherForStudent(stuInfo)

    # Find family, or make new entry
    fam = findOrCreateGuardians( stuInfo )

    print ("Create Student:", firstName, lastName )
    student = Student()
    student.firstname = firstName
    student.lastname = lastName

    student.family = fam
    student.classroom = teacher
    student.student_id = stuInfo[ ColumnName.studentID ]

    db.session.add( student )
    db.session.commit()

def fixTeacherName( rawName ):

    if rawName in TEACHER_NAME_FIX:
        return TEACHER_NAME_FIX[ rawName ]

    # otherwise, flip Last, First
    # NOTE: 2018 Data has this as Last,First
    #namesplit = string.split( rawName, ' ' )
    #fixName = ' '.join(namesplit[1:]) + ', ' + namesplit[0]
    # 2021 data has this matching

    return rawName

GRADE_MISMATCH = []
def updateStudentInfo( stu, stuInfo ):


    #classroom = stuInfo["class"]
    #grade = stuInfo["grade level"]
    teacher = findOrCreateTeacherForStudent(stuInfo)
    # teacherName = fixTeacherName( stuInfo["teacher"] )
    #
    # print "TODO: update student ", stu.displayName(), classroom, grade, teacherName
    # teacher = list(Classroom.query.filter( Classroom.teacher == teacherName ))
    #
    # if len(teacher)==0:
    #     print "COULD NOT FIND TEACHER '%s' (%s)" % ( stuInfo["teacher"], teacherName )
    #     assert( False )
    #
    # teacher = teacher[0]

    # Assign the student
    stu.classroom = teacher
    stu.student_id = stuInfo[ ColumnName.studentID ]
    db.session.commit()

    # # Update the teacher's grade if it doesn't match the ledger
    # if teacher.grade != grade:
    #
    #     print "GRADE MISMATCH '%s' '%s'" % ( teacher.teacher, teacher.grade, grade )
    #     assert ( False )

        # Update the teacher's grade
        #teacher.grade = grade
        #db.session.commit()

        #gm = "%s -- '%s' '%s'" % ( teacher.teacher, teacher.grade, grade )
        #if not gm in GRADE_MISMATCH:
        #    GRADE_MISMATCH.append( gm )

def updateStudent( stuInfo ):
    #print "Update Student " + str(stuInfo)

    firstName = stuInfo[ ColumnName.firstname ]
    lastName = stuInfo [ ColumnName.lastname ]

    stus = list(Student.query.filter( Student.student_id == stuInfo[ ColumnName.studentID ]))

    # if no students match this ID, try for an exact name match
    if (len(stus)==0):
        stus = list(Student.query.filter( and_( func.lower(Student.firstname)==firstName.lower(),
                                                func.lower(Student.lastname)==lastName.lower()
                                                )) )
                                                #Student.student_id==None )) )
        print ("NO student_id match ", firstName, lastName, " trying approx: ", len(stus) )

    if (len(stus) > 1):
        # We don't handle this case because it doesn't come up in our 2017 dataset. Need to use
        # other fields to differentiate if it happens.
        print ( "ERROR: Found multiple students matching name ", firstName, lastName )
        #assert( False )
        return 0

    if len(stus)==0:
        print ( "NEED TO CREATE STUDENT ", stuInfo[ColumnName.studentID],
                stuInfo[ ColumnName.gradelevel], stuInfo[ ColumnName.firstname], stuInfo[ ColumnName.lastname ] )

        stus2 = list(Student.query.filter( or_( func.lower(Student.firstname)==firstName.lower(),
                                        func.lower(Student.lastname)==lastName.lower() )) )

        for ss in stus2:
            print ( "    ? %s '%s' '%s' %s %s" % (ss.student_id, ss.firstname, ss.lastname, ss.classroom.grade, ss.classroom.teacher) )
        createStudent( stuInfo )
    else:
        print( "FOUND Student", stuInfo[ColumnName.studentID], stuInfo[ColumnName.firstname], stuInfo[ColumnName.lastname] )
        updateStudentInfo( stus[0], stuInfo )

    #print "name:", firstName, lastName,  len(list(stus))

    return len(stus)


# NOTE: column names
# first name
# last name
# grade
# course short name
# teacher
# primary contact first name
# primary contact last name
# primary contact email address
# primary contact phone number
# HEREHERE
def importStudentAndGuardianTSV2019( filename ):

    colNum = {}
    totalCols = 0


    unassigned = Classroom.query.filter( Classroom.teacher == 'Unassigned')[0]

    # Delete all unassigned students
    #unstus = Student.query.filter( Student.classroom == unassigned )
    #for stu in unstus:
    #    print "UNSTU", stu.displayName()
    #    if stu.firstname=='Kohta':
    #        continue

    #    db.session.delete(stu)
    #db.session.commit()

    # Remove students from Classrooms
    for stu in Student.query.filter( Student.classroom != unassigned ):

       print ("unassigning ", stu, stu.firstname)
       stu.classroom = unassigned
       db.session.commit()

    notfound = {}
    total = 0

    # TODO: pull this out into a proper tsv parser
    count = 0
    firstLine = True
    for line in codecs.open( filename, 'r', 'utf-8' ):
        lsplit = line.strip().split('\t' )

        if (firstLine):
            print (lsplit )
            totalCols = len(lsplit)
            for cndx in range(len(lsplit)):
                cname = lsplit[cndx].lower()

                # special case some column names
                cname = TSV_CNAME_MAPPING.get( cname, cname )

                print ( f"COLNAME {cname}" )
                colNum[cname] = cndx

            firstLine = False

        else:
            # Replace nulls with ""
            lsplit2 = []
            for item in lsplit:
                if item=='NULL':
                    item=''

                lsplit2.append(item)
            lsplit = lsplit2

            # Pad out the row
            lsplit += [''] * (totalCols - len(lsplit))

            # Mux the student into a dictionary
            stuInfo = {}

            # generate a random student id
            stuInfo[ ColumnName.studentID] = str(10000 + count)
            count += 1

            for k, cndx in colNum.items():
                stuInfo[k] = lsplit[cndx]

            print("STUINFO:", stuInfo )

            # fix teacher name
            teacher = stuInfo[ ColumnName.teacher ]
            teacher = teacher.replace(u'“',u'').replace(u'”',u'').replace(u'"',u'')
            teacher = teacher.strip()
            stuInfo[ ColumnName.teacher ] = teacher

            result = updateStudent( stuInfo )
            if result==0:
                notfound[stuInfo[ColumnName.gradelevel] ] = notfound.get( stuInfo[ColumnName.gradelevel], 0 ) + 1
            total += 1



    #return "zzz"

    print ("GRADE_MISMATCH")
    for g in GRADE_MISMATCH:
        print(g)

    # print len(MISSING_G), "missing guardians"
    # missg = list(MISSING_G)
    # missg.sort()
    # for fname in missg:
    #     print fname

    grades = list(notfound.keys())
    grades.sort()
    nftot = 0
    for g in grades:
        print ("Not found ", g, ": ", notfound[g] )
        nftot += notfound[g]

    print ("Not found", nftot, "of", total, "students")
    return "Done"



